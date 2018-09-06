import numpy as np
import pandas as pd
import pytest
from scipy.spatial import Voronoi
from tyssue.utils import utils
from tyssue import Sheet, SheetGeometry
from tyssue.generation import three_faces_sheet, extrude
from tyssue.generation import hexa_grid2d, from_2d_voronoi
from tyssue.generation import hexa_grid3d, from_3d_voronoi
from numpy.testing import assert_almost_equal, assert_allclose
from tyssue import Monolayer, config
from tyssue import SheetGeometry as geom
from tyssue.topology.base_topology import close_face
from tyssue.core.sheet import get_opposite


def test_to_nd():
    grid = hexa_grid2d(6, 4, 3, 3)
    datasets = from_2d_voronoi(Voronoi(grid))
    sheet = Sheet('test', datasets)
    result = utils._to_3d(sheet.face_df['x'])
    assert result.shape[1] == 3


def test_spec_updater():
    specs = {'face': {'is_active': True,
                      'height': 4,
                      'radial_tension': 0.1},
             'edge': {'x': 2,
                      'y': 1}}
    new_specs = {'face': {'geometry': 'ellipsoidal'}}
    utils.spec_updater(specs, new_specs)
    print(specs)
    assert specs['face']['geometry'] == new_specs['face']['geometry']


def test_set_data_columns():
    dsets, _ = three_faces_sheet()
    specs = {"cell": {'nope': 0},
             "vert": {'new': 100},
             "edge": {'new': 'r'}}
    with pytest.warns(UserWarning):
        utils.set_data_columns(dsets, specs, reset=False)
        assert dsets['vert']['new'].loc[0] == 100
        assert dsets['edge']['new'].loc[0] == 'r'

    specs = {"vert": {'new': 10},
             "edge": {'new': 'v'}}
    utils.set_data_columns(dsets, specs, reset=False)
    assert dsets['edge']['new'].loc[0] == 'r'
    assert dsets['vert']['new'].loc[0] == 100

    utils.set_data_columns(dsets, specs, reset=True)
    assert dsets['vert']['new'].loc[0] == 10
    assert dsets['edge']['new'].loc[0] == 'v'


def test_data_at_opposite():
    sheet = Sheet('emin', *three_faces_sheet())
    geom.update_all(sheet)
    sheet.get_opposite()
    opp = utils.data_at_opposite(sheet, sheet.edge_df['length'], free_value=None)

    assert opp.shape == (sheet.Ne,)
    assert opp.loc[0] == 1.0
    assert ~np.isfinite(opp.loc[1])
    opp = utils.data_at_opposite(sheet, sheet.edge_df['length'], free_value=-1)
    assert opp.loc[1] == -1.0


def test_single_cell():
    grid = hexa_grid3d(6, 4, 3)
    datasets = from_3d_voronoi(Voronoi(grid))
    sheet = Sheet('test', datasets)
    eptm = utils.single_cell(sheet, 1)
    assert len(eptm.edge_df) == len(sheet.edge_df[sheet.edge_df['cell'] == 1])


def test_scaled_unscaled():

    sheet = Sheet('3faces_3D', *three_faces_sheet())
    SheetGeometry.update_all(sheet)

    def mean_area():
        return sheet.face_df.area.mean()

    prev_area = sheet.face_df.area.mean()

    sc_area = utils.scaled_unscaled(mean_area, 2,
                                    sheet, SheetGeometry)
    post_area = sheet.face_df.area.mean()
    assert post_area == prev_area
    assert_almost_equal(sc_area / post_area, 4.)


def test_modify():

    datasets, _ = three_faces_sheet()
    extruded = extrude(datasets, method='translation')
    mono = Monolayer('test', extruded,
                     config.geometry.bulk_spec())
    mono.update_specs(config.dynamics.quasistatic_bulk_spec(),
                      reset=True)
    modifiers = {
        'apical': {
            'edge': {'line_tension': 1.},
            'face': {'contractility': 0.2},
        },
        'basal': {
            'edge': {'line_tension': 3.},
            'face': {'contractility': 0.1},
        }
    }

    utils.modify_segments(mono, modifiers)
    assert mono.edge_df.loc[mono.apical_edges,
                            'line_tension'].unique()[0] == 1.
    assert mono.edge_df.loc[mono.basal_edges,
                            'line_tension'].unique()[0] == 3.


def test_ar_calculation():
    sheet = Sheet('test', *three_faces_sheet())
    SheetGeometry.update_all(sheet)
    sheet.face_df['AR'] = utils.ar_calculation(sheet, coords=['x', 'y'])
    sheet.vert_df['x'] = sheet.vert_df['x'] * 2
    sheet.face_df['AR2'] = utils.ar_calculation(sheet, coords=['x', 'y'])
    assert_allclose(sheet.face_df['AR2'], 2 * sheet.face_df['AR'])
