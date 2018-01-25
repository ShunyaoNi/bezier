# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import threading
import unittest
import unittest.mock

import numpy as np

from tests.unit import utils


SPACING = np.spacing  # pylint: disable=no-member
UNIT_SQUARE = np.asfortranarray([
    [0.0, 0.0],
    [1.0, 0.0],
    [1.0, 1.0],
    [0.0, 1.0],
])


class Test__bbox_intersect(unittest.TestCase):

    @staticmethod
    def _call_function_under_test(nodes1, nodes2):
        from bezier import _geometric_intersection

        return _geometric_intersection._bbox_intersect(nodes1, nodes2)

    def test_intersect(self):
        from bezier import _geometric_intersection

        nodes = UNIT_SQUARE + np.asfortranarray([[0.5, 0.5]])
        result = self._call_function_under_test(UNIT_SQUARE, nodes)
        expected = _geometric_intersection.BoxIntersectionType.INTERSECTION
        self.assertEqual(result, expected)

    def test_far_apart(self):
        from bezier import _geometric_intersection

        nodes = UNIT_SQUARE + np.asfortranarray([[100.0, 100.0]])
        result = self._call_function_under_test(UNIT_SQUARE, nodes)
        expected = _geometric_intersection.BoxIntersectionType.DISJOINT
        self.assertEqual(result, expected)

    def test_disjoint_but_aligned(self):
        from bezier import _geometric_intersection

        nodes = UNIT_SQUARE + np.asfortranarray([[1.0, 2.0]])
        result = self._call_function_under_test(UNIT_SQUARE, nodes)
        expected = _geometric_intersection.BoxIntersectionType.DISJOINT
        self.assertEqual(result, expected)

    def test_tangent(self):
        from bezier import _geometric_intersection

        nodes = UNIT_SQUARE + np.asfortranarray([[1.0, 0.0]])
        result = self._call_function_under_test(UNIT_SQUARE, nodes)
        expected = _geometric_intersection.BoxIntersectionType.TANGENT
        self.assertEqual(result, expected)

    def test_almost_tangent(self):
        from bezier import _geometric_intersection

        x_val = 1.0 + SPACING(1.0)
        nodes = UNIT_SQUARE + np.asfortranarray([[x_val, 0.0]])
        result = self._call_function_under_test(UNIT_SQUARE, nodes)
        expected = _geometric_intersection.BoxIntersectionType.DISJOINT
        self.assertEqual(result, expected)


@utils.needs_speedup
class Test_speedup_bbox_intersect(Test__bbox_intersect):

    @staticmethod
    def _call_function_under_test(nodes1, nodes2):
        from bezier import _speedup

        return _speedup.bbox_intersect(nodes1, nodes2)


class Test_linearization_error(unittest.TestCase):

    @staticmethod
    def _call_function_under_test(nodes):
        from bezier import _geometric_intersection

        return _geometric_intersection.linearization_error(nodes)

    def test_linear(self):
        nodes = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 2.0],
        ])
        error_val = self._call_function_under_test(nodes)
        self.assertEqual(error_val, 0.0)

    def test_degree_elevated_linear(self):
        nodes = np.asfortranarray([
            [0.0, 0.0],
            [0.5, 1.0],
            [1.0, 2.0],
        ])
        error_val = self._call_function_under_test(nodes)
        self.assertEqual(error_val, 0.0)

        nodes = np.asfortranarray([
            [0.0, 0.0],
            [0.25, 0.5],
            [0.5, 1.0],
            [0.75, 1.5],
            [1.0, 2.0],
        ])
        error_val = self._call_function_under_test(nodes)
        self.assertEqual(error_val, 0.0)

    def test_hidden_linear(self):
        # NOTE: This is the line 3 y = 4 x, but with the parameterization
        #       x(s) = 3 s (4 - 3 s).
        nodes = np.asfortranarray([
            [0.0, 0.0],
            [6.0, 8.0],
            [3.0, 4.0],
        ])
        error_val = self._call_function_under_test(nodes)
        # D^2 v = [-9, -12]
        expected = 0.125 * 2 * 1 * 15.0
        self.assertEqual(error_val, expected)

    def test_quadratic(self):
        from bezier import _curve_helpers

        nodes = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
            [5.0, 6.0],
        ])
        # NOTE: This is hand picked so that
        #             d Nodes = [1, 1], [4, 5]
        #           d^2 Nodes = [3, 4]
        #       so that sqrt(3^2 + 4^2) = 5.0
        error_val = self._call_function_under_test(nodes)
        expected = 0.125 * 2 * 1 * 5.0
        self.assertEqual(error_val, expected)

        # For a degree two curve, the 2nd derivative is constant
        # so by subdividing, our error should drop by a factor
        # of (1/2)^2 = 4.
        left_nodes, right_nodes = _curve_helpers.subdivide_nodes(nodes)
        error_left = self._call_function_under_test(left_nodes)
        error_right = self._call_function_under_test(right_nodes)
        self.assertEqual(error_left, 0.25 * expected)
        self.assertEqual(error_right, 0.25 * expected)

    def test_higher_dimension(self):
        nodes = np.asfortranarray([
            [1.5, 0.0, 6.25],
            [3.5, -5.0, 10.25],
            [8.5, 2.0, 10.25],
        ])
        # NOTE: This is hand picked so that
        #             d Nodes = [2, -5, 4], [5, 7, 0]
        #           d^2 Nodes = [3, 12, -4]
        #       so that sqrt(3^2 + 12^2 + 4^2) = 13.0
        error_val = self._call_function_under_test(nodes)
        expected = 0.125 * 2 * 1 * 13.0
        self.assertEqual(error_val, expected)

    def test_hidden_quadratic(self):
        # NOTE: This is the quadratic y = 1 + x^2 / 4, but with the
        #       parameterization x(s) = (3 s - 1)^2.
        nodes = np.asfortranarray([
            [1.0, 1.25],
            [-0.5, 0.5],
            [-0.5, 2.0],
            [1.0, -1.0],
            [4.0, 5.0],
        ])
        error_val = self._call_function_under_test(nodes)
        # D^2 v = [1.5, 2.25], [1.5, -4.5], [1.5, 9]
        expected = 0.125 * 4 * 3 * np.sqrt(1.5**2 + 9.0**2)
        local_eps = abs(SPACING(expected))
        self.assertAlmostEqual(error_val, expected, delta=local_eps)

    def test_cubic(self):
        nodes = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
            [5.0, 6.0],
            [6.0, 7.0],
        ])
        # NOTE: This is hand picked so that
        #             d Nodes = [1, 1], [4, 5], [1, 1]
        #           d^2 Nodes = [3, 4], [-3, -4]
        #       so that sqrt(3^2 + 4^2) = 5.0
        error_val = self._call_function_under_test(nodes)
        expected = 0.125 * 3 * 2 * 5.0
        self.assertEqual(error_val, expected)

    def test_quartic(self):
        nodes = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
            [5.0, 6.0],
            [6.0, 7.0],
            [4.0, 7.0],
        ])
        # NOTE: This is hand picked so that
        #             d Nodes = [1, 1], [4, 5], [1, 1], [-2, 0]
        #           d^2 Nodes = [3, 4], [-3, -4], [-3, -1]
        #       so that sqrt(3^2 + 4^2) = 5.0
        error_val = self._call_function_under_test(nodes)
        expected = 0.125 * 4 * 3 * 5.0
        self.assertEqual(error_val, expected)

    def test_degree_weights_on_the_fly(self):
        nodes = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
            [7.0, 3.0],
            [11.0, 8.0],
            [15.0, 1.0],
            [16.0, -3.0],
        ])
        # NOTE: This is hand picked so that
        #             d Nodes = [1, 1], [6, 2], [4, 5], [4, -7], [1, -4]
        #           d^2 Nodes = [5, 1], [-2, 3], [0, -12], [-3, 3]
        #       so that sqrt(5^2 + 12^2) = 13.0
        error_val = self._call_function_under_test(nodes)
        expected = 0.125 * 5 * 4 * 13.0
        self.assertEqual(error_val, expected)


class Test_segment_intersection(unittest.TestCase):

    @staticmethod
    def _call_function_under_test(start0, end0, start1, end1):
        from bezier import _geometric_intersection

        return _geometric_intersection.segment_intersection(
            start0, end0, start1, end1)

    def _helper(self, intersection, s_val, direction0,
                t_val, direction1, **kwargs):
        start0 = intersection + s_val * direction0
        end0 = intersection + (s_val - 1.0) * direction0
        start1 = intersection + t_val * direction1
        end1 = intersection + (t_val - 1.0) * direction1

        return self._call_function_under_test(
            start0, end0, start1, end1, **kwargs)

    def test_success(self):
        intersection = np.asfortranarray([[1.0, 2.0]])
        s_val = 0.25
        t_val = 0.625
        direction0 = np.asfortranarray([[3.0, 0.5]])
        direction1 = np.asfortranarray([[-2.0, 1.0]])
        # D0 x D1 == 4.0, so there will be no round-off in answer.
        computed_s, computed_t, success = self._helper(
            intersection, s_val, direction0, t_val, direction1)

        self.assertEqual(computed_s, s_val)
        self.assertEqual(computed_t, t_val)
        self.assertTrue(success)

    def test_parallel(self):
        intersection = np.asfortranarray([[0.0, 0.0]])
        s_val = 0.5
        t_val = 0.5
        direction0 = np.asfortranarray([[0.0, 1.0]])
        direction1 = np.asfortranarray([[0.0, 2.0]])
        computed_s, computed_t, success = self._helper(
            intersection, s_val,
            direction0, t_val, direction1)

        self.assertIsNone(computed_s)
        self.assertIsNone(computed_t)
        self.assertFalse(success)


class Test_parallel_different(unittest.TestCase):

    @staticmethod
    def _call_function_under_test(start0, end0, start1, end1):
        from bezier import _geometric_intersection

        return _geometric_intersection.parallel_different(
            start0, end0, start1, end1)

    def test_same_line_no_overlap(self):
        start0 = np.asfortranarray([[0.0, 0.0]])
        end0 = np.asfortranarray([[3.0, 4.0]])
        start1 = np.asfortranarray([[6.0, 8.0]])
        end1 = np.asfortranarray([[9.0, 12.0]])
        self.assertTrue(
            self._call_function_under_test(start0, end0, start1, end1))

    def test_same_line_overlap_at_start(self):
        start0 = np.asfortranarray([[6.0, -3.0]])
        end0 = np.asfortranarray([[-7.0, 1.0]])
        start1 = np.asfortranarray([[1.125, -1.5]])
        end1 = np.asfortranarray([[-5.375, 0.5]])
        self.assertFalse(
            self._call_function_under_test(start0, end0, start1, end1))

    def test_same_line_overlap_at_end(self):
        start0 = np.asfortranarray([[1.0, 2.0]])
        end0 = np.asfortranarray([[3.0, 5.0]])
        start1 = np.asfortranarray([[-0.5, -0.25]])
        end1 = np.asfortranarray([[2.0, 3.5]])
        self.assertFalse(
            self._call_function_under_test(start0, end0, start1, end1))

    def test_same_line_contained(self):
        start0 = np.asfortranarray([[-9.0, 0.0]])
        end0 = np.asfortranarray([[4.0, 5.0]])
        start1 = np.asfortranarray([[23.5, 12.5]])
        end1 = np.asfortranarray([[-25.25, -6.25]])
        self.assertFalse(
            self._call_function_under_test(start0, end0, start1, end1))

    def test_different_line(self):
        start0 = np.asfortranarray([[3.0, 2.0]])
        end0 = np.asfortranarray([[3.0, 0.75]])
        start1 = np.asfortranarray([[0.0, 0.0]])
        end1 = np.asfortranarray([[0.0, 2.0]])
        self.assertTrue(
            self._call_function_under_test(start0, end0, start1, end1))


class Test_wiggle_pair(unittest.TestCase):

    @staticmethod
    def _call_function_under_test(s_val, t_val):
        from bezier import _geometric_intersection

        return _geometric_intersection.wiggle_pair(s_val, t_val)

    def test_success(self):
        s_val = float.fromhex('-0x1.fffffffffffffp-46')
        t_val = 0.75
        new_s, new_t = self._call_function_under_test(s_val, t_val)
        self.assertEqual(new_s, 0.0)
        self.assertEqual(new_t, t_val)

    def test_failure(self):
        with self.assertRaises(ValueError):
            self._call_function_under_test(-0.5, 0.5)


class Test_from_linearized(utils.NumPyTestCase):

    @staticmethod
    def _call_function_under_test(first, second, intersections):
        from bezier import _geometric_intersection

        return _geometric_intersection.from_linearized(
            first, second, intersections)

    def test_success(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [0.5, 1.0],
            [1.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        # NOTE: This curve isn't close to linear, but that's OK.
        lin1 = make_linearization(curve1, error=np.nan)

        nodes2 = np.asfortranarray([
            [0.0, 1.0],
            [0.5, 1.0],
            [1.0, 0.0],
        ])
        curve2 = subdivided_curve(nodes2)
        # NOTE: This curve isn't close to linear, but that's OK.
        lin2 = make_linearization(curve2, error=np.nan)

        intersections = []
        self.assertIsNone(
            self._call_function_under_test(lin1, lin2, intersections))
        self.assertEqual(intersections, [(0.5, 0.5)])

    def test_failure(self):
        # The bounding boxes intersect but the lines do not.
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        lin1 = make_linearization(curve1, error=0.0)

        nodes2 = np.asfortranarray([
            [1.75, -0.75],
            [0.75, 0.25],
        ])
        curve2 = subdivided_curve(nodes2)
        lin2 = make_linearization(curve2, error=0.0)

        intersections = []
        self.assertIsNone(
            self._call_function_under_test(lin1, lin2, intersections))
        self.assertEqual(len(intersections), 0)

    def _no_intersect_help(self, swap=False):
        # The bounding boxes intersect but the lines do not.
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        lin1 = make_linearization(curve1, error=0.0)

        nodes2 = np.asfortranarray([
            [1.75, -0.75],
            [0.75, 0.25],
        ])
        curve2 = subdivided_curve(nodes2)
        lin2 = make_linearization(curve2, error=0.0)

        if swap:
            lin1, lin2 = lin2, lin1

        intersections = []
        return_value = self._call_function_under_test(
            lin1, lin2, intersections)
        self.assertIsNone(return_value)
        self.assertEqual(intersections, [])

    def test_no_intersection_bad_t(self):
        self._no_intersect_help()

    def test_no_intersection_bad_s(self):
        self._no_intersect_help(swap=True)

    def _no_intersect_help_non_line(self, swap=False):
        # The bounding boxes intersect but the lines do not.
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [0.5, 0.0],
            [1.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        lin1 = make_linearization(curve1, error=0.25)

        nodes2 = np.asfortranarray([
            [1.75, -0.75],
            [1.25, -0.75],
            [0.75, 0.25],
        ])
        curve2 = subdivided_curve(nodes2)
        lin2 = make_linearization(curve2, error=0.25)

        if swap:
            lin1, lin2 = lin2, lin1

        intersections = []
        return_value = self._call_function_under_test(
            lin1, lin2, intersections)
        self.assertIsNone(return_value)
        self.assertEqual(intersections, [])

    def test_no_intersection_bad_t_non_line(self):
        self._no_intersect_help_non_line()

    def test_no_intersection_bad_s_non_line(self):
        self._no_intersect_help_non_line(swap=True)

    def test_parallel_intersection(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        lin1 = make_linearization(curve1, error=0.0)

        nodes2 = np.asfortranarray([
            [0.0, 1.0],
            [1.0, 2.0],
        ])
        curve2 = subdivided_curve(nodes2)
        lin2 = make_linearization(curve2, error=0.0)

        intersections = []
        return_value = self._call_function_under_test(
            lin1, lin2, intersections)
        self.assertIsNone(return_value)
        self.assertEqual(intersections, [])

    def test_same_line_intersection(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        lin1 = make_linearization(curve1, error=0.0)

        nodes2 = np.asfortranarray([
            [0.5, 0.5],
            [3.0, 3.0],
        ])
        curve2 = subdivided_curve(nodes2)
        lin2 = make_linearization(curve2, error=0.0)

        intersections = []
        with self.assertRaises(NotImplementedError):
            self._call_function_under_test(lin1, lin2, intersections)

        self.assertEqual(intersections, [])

    def test_parallel_non_degree_one_disjoint(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        lin1 = make_linearization(curve1, error=0.0)

        nodes2 = np.asfortranarray([
            [2.0, 2.0],
            [2.5009765625, 2.5009765625],
            [3.0, 3.0],
        ])
        curve2 = subdivided_curve(nodes2)
        lin2 = make_linearization(curve2, error=np.nan)

        intersections = []
        return_value = self._call_function_under_test(
            lin1, lin2, intersections)
        self.assertIsNone(return_value)
        self.assertEqual(intersections, [])

    def test_parallel_non_degree_not_disjoint(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        lin1 = make_linearization(curve1, error=0.0)

        nodes2 = np.asfortranarray([
            [0.5, 0.75],
            [1.0009765625, 1.2509765625],
            [1.5, 1.75],
        ])
        curve2 = subdivided_curve(nodes2)
        lin2 = make_linearization(curve2, error=np.nan)

        intersections = []
        with self.assertRaises(NotImplementedError):
            self._call_function_under_test(lin1, lin2, intersections)

        self.assertEqual(intersections, [])

    def test_wiggle_failure(self):
        from bezier import _curve_helpers
        from bezier import _geometric_intersection

        nodes1 = np.asfortranarray([
            [-0.7993236103108717, -0.21683567278362156],
            [-0.8072986524226636, -0.21898490744674426],
            [-0.8152736945344552, -0.2211341421098668],
            [-0.8232487366462472, -0.2232833767729893],
        ])
        curve1 = subdivided_curve(nodes1)
        lin1 = make_linearization(curve1)

        original_nodes2 = np.asfortranarray([
            [-0.7838204403623438, -0.25519640597397464],
            [-0.7894577677825452, -0.24259531488131633],
            [-0.7946421067207265, -0.22976394420044136],
            [-0.799367666650849, -0.21671303774854855],
        ])
        start = 0.99609375
        nodes2 = _curve_helpers.specialize_curve(original_nodes2, start, 1.0)
        curve2 = _geometric_intersection.SubdividedCurve(
            nodes2, original_nodes2, start=start)
        lin2 = make_linearization(curve2)

        intersections = []
        with self.assertRaises(ValueError) as exc_info:
            self._call_function_under_test(lin1, lin2, intersections)

        self.assertEqual(intersections, [])
        exc_args = exc_info.exception.args
        self.assertEqual(len(exc_args), 3)
        self.assertEqual(
            exc_args[0], _geometric_intersection._AT_LEAST_ONE_OUTSIDE)


class Test_add_intersection(unittest.TestCase):

    @staticmethod
    def _call_function_under_test(s, t, intersections):
        from bezier import _geometric_intersection

        return _geometric_intersection.add_intersection(s, t, intersections)

    def test_new(self):
        intersections = [(0.5, 0.5)]
        self.assertIsNone(
            self._call_function_under_test(0.75, 0.25, intersections))

        expected = [
            (0.5, 0.5),
            (0.75, 0.25),
        ]
        self.assertEqual(intersections, expected)

    def test_existing(self):
        intersections = [(0.0, 1.0)]
        self.assertIsNone(
            self._call_function_under_test(0.0, 1.0, intersections))

        self.assertEqual(intersections, [(0.0, 1.0)])

    def test_ulp_wiggle(self):
        from bezier import _geometric_intersection

        delta = 3 * SPACING(0.5)
        intersections = [(0.5, 0.5)]
        s_val = 0.5 + delta
        t_val = 0.5

        patch = unittest.mock.patch.object(
            _geometric_intersection, '_SIMILAR_ULPS', new=10)
        with patch:
            self.assertIsNone(
                self._call_function_under_test(s_val, t_val, intersections))
            # No change since delta is within 10 ULPs.
            self.assertEqual(intersections, [(0.5, 0.5)])

        patch = unittest.mock.patch.object(
            _geometric_intersection, '_SIMILAR_ULPS', new=3)
        with patch:
            self.assertIsNone(
                self._call_function_under_test(s_val, t_val, intersections))
            # No change since delta is within 3 ULPs.
            self.assertEqual(intersections, [(0.5, 0.5)])

        patch = unittest.mock.patch.object(
            _geometric_intersection, '_SIMILAR_ULPS', new=2)
        with patch:
            self.assertIsNone(
                self._call_function_under_test(s_val, t_val, intersections))
            # Add new intersection since delta is not within 2 ULPs.
            self.assertEqual(intersections, [(0.5, 0.5), (s_val, t_val)])


class Test_endpoint_check(utils.NumPyTestCase):

    @staticmethod
    def _call_function_under_test(
            first, node_first, s, second, node_second, t, intersections):
        from bezier import _geometric_intersection

        return _geometric_intersection.endpoint_check(
            first, node_first, s, second, node_second, t, intersections)

    def test_not_close(self):
        node_first = np.asfortranarray([[0.0, 0.0]])
        node_second = np.asfortranarray([[1.0, 1.0]])
        intersections = []
        self._call_function_under_test(
            None, node_first, None, None, node_second, None, intersections)
        self.assertEqual(intersections, [])

    def test_same(self):
        nodes_first = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
        ])
        first = subdivided_curve(nodes_first)
        nodes_second = np.asfortranarray([
            [1.0, 1.0],
            [2.0, 1.0],
        ])
        second = subdivided_curve(nodes_second)

        s_val = 1.0
        node_first = np.asfortranarray(first.nodes[[1], :])
        t_val = 0.0
        node_second = np.asfortranarray(second.nodes[[0], :])

        intersections = []
        self._call_function_under_test(
            first, node_first, s_val,
            second, node_second, t_val, intersections)

        self.assertEqual(intersections, [(s_val, t_val)])

    def test_subcurves_middle(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [0.5, 1.0],
            [1.0, 0.0],
        ])
        root1 = subdivided_curve(nodes1)
        first, _ = root1.subdivide()
        nodes2 = np.asfortranarray([
            [1.0, 1.5],
            [0.0, 0.5],
            [1.0, -0.5],
        ])
        root2 = subdivided_curve(nodes2)
        _, second = root2.subdivide()

        s_val = 1.0
        node_first = np.asfortranarray(first.nodes[[2], :])
        t_val = 0.0
        node_second = np.asfortranarray(second.nodes[[0], :])

        intersections = []
        self._call_function_under_test(
            first, node_first, s_val,
            second, node_second, t_val, intersections)

        self.assertEqual(intersections, [(0.5, 0.5)])


class Test_tangent_bbox_intersection(utils.NumPyTestCase):

    @staticmethod
    def _call_function_under_test(first, second, intersections):
        from bezier import _geometric_intersection

        return _geometric_intersection.tangent_bbox_intersection(
            first, second, intersections)

    def test_one_endpoint(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 2.0],
            [2.0, 0.0],
        ])
        curve1 = subdivided_curve(nodes1)
        nodes2 = np.asfortranarray([
            [2.0, 0.0],
            [3.0, 2.0],
            [4.0, 0.0],
        ])
        curve2 = subdivided_curve(nodes2)

        intersections = []
        self.assertIsNone(
            self._call_function_under_test(curve1, curve2, intersections))
        self.assertEqual(intersections, [(1.0, 0.0)])

    def test_two_endpoints(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [-1.0, 0.5],
            [0.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        nodes2 = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 0.5],
            [0.0, 1.0],
        ])
        curve2 = subdivided_curve(nodes2)

        intersections = []
        self.assertIsNone(
            self._call_function_under_test(curve1, curve2, intersections))
        expected = [
            (0.0, 0.0),
            (1.0, 1.0),
        ]
        self.assertEqual(intersections, expected)

    def test_no_endpoints(self):
        # Lines have tangent bounding boxes but don't intersect.
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [2.0, 1.0],
        ])
        curve1 = subdivided_curve(nodes1)
        nodes2 = np.asfortranarray([
            [0.5, 1.0],
            [2.5, 2.0],
        ])
        curve2 = subdivided_curve(nodes2)

        intersections = []
        self.assertIsNone(
            self._call_function_under_test(curve1, curve2, intersections))
        self.assertEqual(intersections, [])


class Test_bbox_line_intersect(utils.NumPyTestCase):

    @staticmethod
    def _call_function_under_test(nodes, line_start, line_end):
        from bezier import _geometric_intersection

        return _geometric_intersection.bbox_line_intersect(
            nodes, line_start, line_end)

    def test_start_in_bbox(self):
        from bezier import _geometric_intersection

        line_start = np.asfortranarray([[0.5, 0.5]])
        line_end = np.asfortranarray([[0.5, 1.5]])

        result = self._call_function_under_test(
            UNIT_SQUARE, line_start, line_end)
        expected = _geometric_intersection.BoxIntersectionType.INTERSECTION
        self.assertEqual(result, expected)

    def test_end_in_bbox(self):
        from bezier import _geometric_intersection

        line_start = np.asfortranarray([[-1.0, 0.5]])
        line_end = np.asfortranarray([[0.5, 0.5]])

        result = self._call_function_under_test(
            UNIT_SQUARE, line_start, line_end)
        expected = _geometric_intersection.BoxIntersectionType.INTERSECTION
        self.assertEqual(result, expected)

    def test_segment_intersect_bbox_bottom(self):
        from bezier import _geometric_intersection

        line_start = np.asfortranarray([[0.5, -0.5]])
        line_end = np.asfortranarray([[0.5, 1.5]])

        result = self._call_function_under_test(
            UNIT_SQUARE, line_start, line_end)
        expected = _geometric_intersection.BoxIntersectionType.INTERSECTION
        self.assertEqual(result, expected)

    def test_segment_intersect_bbox_right(self):
        from bezier import _geometric_intersection

        line_start = np.asfortranarray([[-0.5, 0.5]])
        line_end = np.asfortranarray([[1.5, 0.5]])

        result = self._call_function_under_test(
            UNIT_SQUARE, line_start, line_end)
        expected = _geometric_intersection.BoxIntersectionType.INTERSECTION
        self.assertEqual(result, expected)

    def test_segment_intersect_bbox_top(self):
        from bezier import _geometric_intersection

        line_start = np.asfortranarray([[-0.25, 0.5]])
        line_end = np.asfortranarray([[0.5, 1.25]])

        result = self._call_function_under_test(
            UNIT_SQUARE, line_start, line_end)
        expected = _geometric_intersection.BoxIntersectionType.INTERSECTION
        self.assertEqual(result, expected)

    def test_disjoint(self):
        from bezier import _geometric_intersection

        line_start = np.asfortranarray([[2.0, 2.0]])
        line_end = np.asfortranarray([[2.0, 5.0]])

        result = self._call_function_under_test(
            UNIT_SQUARE, line_start, line_end)
        expected = _geometric_intersection.BoxIntersectionType.DISJOINT
        self.assertEqual(result, expected)


class Test_intersect_one_round(utils.NumPyTestCase):

    # NOTE: QUADRATIC1 is a specialization of [0, 0], [1/2, 1], [1, 1]
    #       onto the interval [1/4, 1].
    QUADRATIC1 = np.asfortranarray([
        [0.25, 0.4375],
        [0.625, 1.0],
        [1.0, 1.0],
    ])
    # NOTE: QUADRATIC2 is a specialization of [0, 1], [1/2, 1], [1, 0]
    #       onto the interval [0, 3/4].
    QUADRATIC2 = np.asfortranarray([
        [0.0, 1.0],
        [0.375, 1.0],
        [0.75, 0.4375],
    ])
    LINE1 = np.asfortranarray([
        [0.0, 0.0],
        [1.0, 1.0],
    ])
    LINE2 = np.asfortranarray([
        [0.0, 1.0],
        [1.0, 0.0],
    ])

    @staticmethod
    def _call_function_under_test(candidates, intersections):
        from bezier import _geometric_intersection

        return _geometric_intersection.intersect_one_round(
            candidates, intersections)

    def _curves_compare(self, curve1, curve2):
        from bezier import _geometric_intersection

        if isinstance(curve1, _geometric_intersection.Linearization):
            self.assertIsInstance(
                curve2, _geometric_intersection.Linearization)
            # We just check identity, since we assume a ``Linearization``
            # can't be subdivided.
            self.assertIs(curve1, curve2)
        else:
            self.assertIsInstance(
                curve1, _geometric_intersection.SubdividedCurve)
            self.assertIsInstance(
                curve2, _geometric_intersection.SubdividedCurve)
            self.assertIs(curve1.original_nodes, curve2.original_nodes)
            self.assertEqual(curve1.start, curve2.start)
            self.assertEqual(curve1.end, curve2.end)
            self.assertEqual(curve1.nodes, curve2.nodes)

    def _candidates_compare(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for first, second in zip(actual, expected):
            self.assertEqual(len(first), 2)
            self.assertEqual(len(second), 2)
            self._curves_compare(first[0], second[0])
            self._curves_compare(first[1], second[1])

    def test_simple(self):
        curve1 = subdivided_curve(self.QUADRATIC1)
        curve2 = subdivided_curve(self.QUADRATIC2)
        candidates = [(curve1, curve2)]
        next_candidates = self._call_function_under_test(
            candidates, [])

        left1, right1 = curve1.subdivide()
        left2, right2 = curve2.subdivide()
        expected = [
            (left1, left2),
            (left1, right2),
            (right1, left2),
            (right1, right2),
        ]
        self._candidates_compare(next_candidates, expected)

    def test_first_linearized(self):
        curve1 = subdivided_curve(self.LINE1)
        lin1 = make_linearization(curve1, error=0.0)
        curve2 = subdivided_curve(self.QUADRATIC2)

        intersections = []
        next_candidates = self._call_function_under_test(
            [(lin1, curve2)], intersections)

        self.assertEqual(intersections, [])
        left2, right2 = curve2.subdivide()
        expected = [
            (lin1, left2),
            (lin1, right2),
        ]
        self._candidates_compare(next_candidates, expected)

    def test_second_linearized(self):
        curve1 = subdivided_curve(self.QUADRATIC1)
        curve2 = subdivided_curve(self.LINE2)
        lin2 = make_linearization(curve2, error=0.0)

        intersections = []
        next_candidates = self._call_function_under_test(
            [(curve1, lin2)], intersections)

        self.assertEqual(intersections, [])
        left1, right1 = curve1.subdivide()
        expected = [
            (left1, lin2),
            (right1, lin2),
        ]
        self._candidates_compare(next_candidates, expected)

    def test_both_linearized(self):
        curve1 = subdivided_curve(self.LINE1)
        lin1 = make_linearization(curve1, error=0.0)
        curve2 = subdivided_curve(self.LINE2)
        lin2 = make_linearization(curve2, error=0.0)

        intersections = []
        next_candidates = self._call_function_under_test(
            [(lin1, lin2)], intersections)
        self.assertEqual(next_candidates, [])
        self.assertEqual(intersections, [(0.5, 0.5)])

    def test_failure_due_to_parallel(self):
        from bezier import _geometric_intersection

        curve1 = subdivided_curve(self.LINE1)
        lin1 = make_linearization(curve1, error=0.0)
        nodes2 = np.asfortranarray([
            [0.5, 0.5],
            [3.0, 3.0],
        ])
        curve2 = subdivided_curve(nodes2)
        lin2 = make_linearization(curve2, error=0.0)

        intersections = []
        with self.assertRaises(NotImplementedError) as exc_info:
            self._call_function_under_test([(lin1, lin2)], intersections)

        exc_args = exc_info.exception.args
        self.assertEqual(
            exc_args, (_geometric_intersection._SEGMENTS_PARALLEL,))
        self.assertEqual(intersections, [])

    def test_disjoint_bboxes(self):
        curve1 = subdivided_curve(self.QUADRATIC1)
        nodes2 = np.asfortranarray([
            [1.0, 1.25],
            [0.0, 2.0],
        ])
        curve2 = subdivided_curve(nodes2)
        lin2 = make_linearization(curve2, error=0.0)

        intersections = []
        next_candidates = self._call_function_under_test(
            [(curve1, lin2)], intersections)
        self.assertEqual(next_candidates, [])
        self.assertEqual(intersections, [])

    def test_tangent_bboxes(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [0.5, 1.0],
            [1.0, 0.0],
        ])
        curve1 = subdivided_curve(nodes1)
        nodes2 = np.asfortranarray([
            [1.0, 0.0],
            [1.5, 0.5],
            [2.0, -0.25],
        ])
        curve2 = subdivided_curve(nodes2)

        intersections = []
        next_candidates = self._call_function_under_test(
            [(curve1, curve2)], intersections)
        self.assertEqual(next_candidates, [])
        self.assertEqual(intersections, [(1.0, 0.0)])


class Test__all_intersections(utils.NumPyTestCase):

    @staticmethod
    def _call_function_under_test(nodes_first, nodes_second, **kwargs):
        from bezier import _geometric_intersection

        return _geometric_intersection._all_intersections(
            nodes_first, nodes_second, **kwargs)

    def test_no_intersections(self):
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
        ])
        nodes2 = np.asfortranarray([
            [3.0, 3.0],
            [4.0, 3.0],
        ])
        intersections = self._call_function_under_test(nodes1, nodes2)
        self.assertEqual(intersections.shape, (0, 2))

    def test_quadratics_intersect_once(self):
        # NOTE: ``nodes1`` is a specialization of [0, 0], [1/2, 1], [1, 1]
        #       onto the interval [1/4, 1] and ``nodes`` is a specialization
        #       of [0, 1], [1/2, 1], [1, 0] onto the interval [0, 3/4].
        #       We expect them to intersect at s = 1/3, t = 2/3, which is
        #       the point [1/2, 3/4].
        nodes1 = np.asfortranarray([
            [0.25, 0.4375],
            [0.625, 1.0],
            [1.0, 1.0],
        ])
        nodes2 = np.asfortranarray([
            [0.0, 1.0],
            [0.375, 1.0],
            [0.75, 0.4375],
        ])
        s_val = 1.0 / 3.0
        t_val = 2.0 / 3.0
        intersections = self._call_function_under_test(nodes1, nodes2)

        # Due to round-off, the answer may be wrong by a tiny wiggle.
        self.assertEqual(intersections.shape, (1, 2))
        self.assertAlmostEqual(
            intersections[0, 0], s_val, delta=SPACING(s_val))
        self.assertEqual(intersections[0, 1], t_val)

    def test_parallel_failure(self):
        from bezier import _geometric_intersection

        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [0.375, 0.75],
            [0.75, 0.375],
        ])
        nodes2 = np.asfortranarray([
            [0.25, 0.625],
            [0.625, 0.25],
            [1.0, 1.0],
        ])
        with self.assertRaises(NotImplementedError) as exc_info:
            self._call_function_under_test(nodes1, nodes2)

        exc_args = exc_info.exception.args
        self.assertEqual(
            exc_args, (_geometric_intersection._SEGMENTS_PARALLEL,))

    def test_too_many_candidates(self):
        from bezier import _geometric_intersection

        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [-0.5, 1.5],
            [1.0, 1.0],
        ])
        nodes2 = np.asfortranarray([
            [-1.0, 1.0],
            [0.5, 0.5],
            [0.0, 2.0],
        ])
        with self.assertRaises(NotImplementedError) as exc_info:
            self._call_function_under_test(nodes1, nodes2)

        exc_args = exc_info.exception.args
        expected = _geometric_intersection._TOO_MANY_TEMPLATE.format(88)
        self.assertEqual(exc_args, (expected,))

    def test_non_convergence(self):
        from bezier import _geometric_intersection

        multiplier = 16384.0
        nodes1 = multiplier * np.asfortranarray([
            [0.0, 0.0],
            [4.5, 9.0],
            [9.0, 0.0],
        ])
        nodes2 = multiplier * np.asfortranarray([
            [0.0, 8.0],
            [6.0, 0.0],
        ])
        with self.assertRaises(ValueError) as exc_info:
            self._call_function_under_test(nodes1, nodes2)

        exc_args = exc_info.exception.args
        expected = _geometric_intersection._NO_CONVERGE_TEMPLATE.format(
            _geometric_intersection._MAX_INTERSECT_SUBDIVISIONS)
        self.assertEqual(exc_args, (expected,))

    def test_duplicates(self):
        # After three subdivisions, there are 8 pairs of curve segments
        # which have bounding boxes that touch at corners (these corners are
        # also intersections). This test makes sure the duplicates are
        # de-duplicated.
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [0.5, 1.0],
            [1.0, 0.0],
        ])
        nodes2 = np.asfortranarray([
            [0.0, 0.75],
            [0.5, -0.25],
            [1.0, 0.75],
        ])
        intersections = self._call_function_under_test(nodes1, nodes2)
        expected = np.asfortranarray([
            [0.25, 0.25],
            [0.75, 0.75],
        ])
        self.assertEqual(intersections, expected)

    def _check_wiggle_fail(self, exc_info):
        from bezier import _geometric_intersection

        exc_args = exc_info.exception.args
        self.assertEqual(len(exc_args), 3)
        self.assertEqual(
            exc_args[0], _geometric_intersection._AT_LEAST_ONE_OUTSIDE)

    def test_wiggle_failure(self):
        nodes1 = np.asfortranarray([
            [-0.7838204403623438, -0.25519640597397464],
            [-0.7894577677825452, -0.24259531488131633],
            [-0.7946421067207265, -0.22976394420044136],
            [-0.799367666650849, -0.21671303774854855],
        ])
        nodes2 = np.asfortranarray([
            [-0.7993236103108717, -0.21683567278362156],
            [-0.8072986524226636, -0.21898490744674426],
            [-0.8152736945344552, -0.2211341421098668],
            [-0.8232487366462472, -0.2232833767729893],
        ])

        with self.assertRaises(ValueError) as exc_info:
            self._call_function_under_test(nodes1, nodes2)
        self._check_wiggle_fail(exc_info)

        with self.assertRaises(ValueError) as exc_info:
            self._call_function_under_test(nodes2, nodes1)
        self._check_wiggle_fail(exc_info)


@utils.needs_speedup
class Test_speedup_all_intersections(Test__all_intersections):

    @staticmethod
    def _call_function_under_test(nodes_first, nodes_second, **kwargs):
        from bezier import _speedup

        return _speedup.curve_intersections(
            nodes_first, nodes_second, **kwargs)

    @staticmethod
    def reset_curves_workspace(workspace_size):
        from bezier import _speedup

        return _speedup.reset_curves_workspace(workspace_size)

    @staticmethod
    def curves_workspace_size():
        from bezier import _speedup

        return _speedup.curves_workspace_size()

    def _check_wiggle_fail(self, exc_info):
        self.assertEqual(
            exc_info.exception.args, ('outside of unit interval',))

    def test_workspace_resize(self):
        nodes1 = np.asfortranarray([
            [-3.0, 0.0],
            [5.0, 0.0],
        ])
        nodes2 = np.asfortranarray([
            [-7.0, -9.0],
            [9.0, 13.0],
            [-7.0, -13.0],
            [9.0, 9.0],
        ])
        # NOTE: These curves intersect 3 times, so a workspace of
        #       2 is not large enough.
        self.reset_curves_workspace(2)
        intersections = self._call_function_under_test(nodes1, nodes2)
        expected = np.asfortranarray([
            [0.5, 0.5],
            [0.375, 0.25],
            [0.625, 0.75],
        ])
        self.assertEqual(intersections, expected)
        # Make sure the workspace was resized.
        self.assertEqual(self.curves_workspace_size(), 3)

    def test_workspace_too_small(self):
        from bezier import _speedup

        nodes1 = np.asfortranarray([
            [-3.0, 0.0],
            [5.0, 0.0],
        ])
        nodes2 = np.asfortranarray([
            [-7.0, -9.0],
            [9.0, 13.0],
            [-7.0, -13.0],
            [9.0, 9.0],
        ])
        # NOTE: These curves intersect 3 times, so a workspace of
        #       2 is not large enough.
        self.reset_curves_workspace(2)
        with self.assertRaises(ValueError) as exc_info:
            self._call_function_under_test(
                nodes1, nodes2, allow_resize=False)

        exc_args = exc_info.exception.args
        expected = _speedup.TOO_SMALL_TEMPLATE.format(3, 2)
        self.assertEqual(exc_args, (expected,))
        # Make sure the workspace was **not** resized.
        self.assertEqual(self.curves_workspace_size(), 2)


class Test__set_max_candidates(utils.NumPyTestCase):
    # NOTE: This is also a test for ``_get_max_candidates``.

    @staticmethod
    def _call_function_under_test(num_candidates):
        from bezier import _geometric_intersection

        return _geometric_intersection._set_max_candidates(num_candidates)

    @staticmethod
    def get_max_candidates():
        from bezier import _geometric_intersection

        return _geometric_intersection._get_max_candidates()

    def test_it(self):
        curr_candidates = self.get_max_candidates()

        new_candidates = 55
        return_value = self._call_function_under_test(new_candidates)
        self.assertIsNone(return_value)
        self.assertEqual(self.get_max_candidates(), new_candidates)

        # Put things back the way they were.
        self._call_function_under_test(curr_candidates)

    @staticmethod
    def intersect(nodes1, nodes2):
        from bezier import _geometric_intersection

        return _geometric_intersection._all_intersections(nodes1, nodes2)

    def test_on_intersection(self):
        from bezier import _geometric_intersection

        template = _geometric_intersection._TOO_MANY_TEMPLATE
        # B1(s) = [s(2s - 1), s(3 - 2s)]
        # f1(x, y) = 4(x^2 + 2xy - 3x + y^2 - y)
        nodes1 = np.asfortranarray([
            [0.0, 0.0],
            [-0.5, 1.5],
            [1.0, 1.0],
        ])
        # B2(s) = [(1 - 2s)(s - 1), 2s^2 - s + 1]
        # f2(x, y) = 4(x^2 + 2xy - x + y^2 - 3y + 2)
        nodes2 = np.asfortranarray([
            [-1.0, 1.0],
            [0.5, 0.5],
            [0.0, 2.0],
        ])

        curr_candidates = self.get_max_candidates()
        self.assertEqual(curr_candidates, 64)

        # First, show failure with the default.
        with self.assertRaises(NotImplementedError) as exc_info:
            self.intersect(nodes1, nodes2)
        self.assertEqual(exc_info.exception.args, (template.format(88),))

        # Then, show failure with twice the limit.
        self._call_function_under_test(128)
        with self.assertRaises(NotImplementedError) as exc_info:
            self.intersect(nodes1, nodes2)
        self.assertEqual(exc_info.exception.args, (template.format(184),))

        # Then, show failure with (almost) four times the limit.
        self._call_function_under_test(255)
        with self.assertRaises(NotImplementedError) as exc_info:
            self.intersect(nodes1, nodes2)
        self.assertEqual(exc_info.exception.args, (template.format(256),))

        # Then, show success.
        self._call_function_under_test(256)
        result = self.intersect(nodes1, nodes2)
        # f2(*B1(s)) = 8(2s - 1)^2
        # f1(*B2(t)) = 8(2t - 1)^2
        self.assertEqual(result, np.asfortranarray([[0.5, 0.5]]))

        # Put things back the way they were.
        self._call_function_under_test(curr_candidates)


@utils.needs_speedup
class Test_speedup_set_max_candidates(Test__set_max_candidates):
    # NOTE: This is also a test for the ``get_max_candidates`` speedup.

    @staticmethod
    def _call_function_under_test(num_candidates):
        from bezier import _speedup

        return _speedup.set_max_candidates(num_candidates)

    @staticmethod
    def get_max_candidates():
        from bezier import _speedup

        return _speedup.get_max_candidates()

    @staticmethod
    def intersect(nodes1, nodes2):
        from bezier import _speedup

        return _speedup.curve_intersections(nodes1, nodes2)


class Test__set_similar_ulps(unittest.TestCase):
    # NOTE: This is also a test for ``_get_similar_ulps``.

    @staticmethod
    def _call_function_under_test(num_bits):
        from bezier import _geometric_intersection

        return _geometric_intersection._set_similar_ulps(num_bits)

    @staticmethod
    def get_similar_ulps():
        from bezier import _geometric_intersection

        return _geometric_intersection._get_similar_ulps()

    def test_it(self):
        curr_num_bits = self.get_similar_ulps()

        new_num_bits = 4
        return_value = self._call_function_under_test(new_num_bits)
        self.assertIsNone(return_value)
        self.assertEqual(self.get_similar_ulps(), new_num_bits)

        # Put things back the way they were.
        self._call_function_under_test(curr_num_bits)


@utils.needs_speedup
class Test_speedup_set_similar_ulps(Test__set_similar_ulps):
    # NOTE: This is also a test for the ``get_similar_ulps`` speedup.

    @staticmethod
    def _call_function_under_test(num_bits):
        from bezier import _speedup

        return _speedup.set_similar_ulps(num_bits)

    @staticmethod
    def get_similar_ulps():
        from bezier import _speedup

        return _speedup.get_similar_ulps()


class TestSubdividedCurve(utils.NumPyTestCase):

    @staticmethod
    def _get_target_class():
        from bezier import _geometric_intersection

        return _geometric_intersection.SubdividedCurve

    def _make_one(self, *args, **kwargs):
        klass = self._get_target_class()
        return klass(*args, **kwargs)

    def test_constructor_defaults(self):
        curve = self._make_one(
            unittest.mock.sentinel.nodes,
            unittest.mock.sentinel.original_nodes)
        self.assertIs(curve.nodes, unittest.mock.sentinel.nodes)
        self.assertIs(
            curve.original_nodes, unittest.mock.sentinel.original_nodes)
        self.assertEqual(curve.start, 0.0)
        self.assertEqual(curve.end, 1.0)

    def test_constructor_explicit(self):
        curve = self._make_one(
            unittest.mock.sentinel.nodes,
            unittest.mock.sentinel.original_nodes,
            start=3.0, end=5.0)
        self.assertIs(curve.nodes, unittest.mock.sentinel.nodes)
        self.assertIs(
            curve.original_nodes, unittest.mock.sentinel.original_nodes)
        self.assertEqual(curve.start, 3.0)
        self.assertEqual(curve.end, 5.0)

    def test___dict___property(self):
        curve = self._make_one(
            unittest.mock.sentinel.nodes,
            unittest.mock.sentinel.original_nodes,
            start=0.25, end=0.75)
        props_dict = curve.__dict__
        expected = {
            'nodes': unittest.mock.sentinel.nodes,
            'original_nodes': unittest.mock.sentinel.original_nodes,
            'start': 0.25,
            'end': 0.75,
        }
        self.assertEqual(props_dict, expected)
        # Check that modifying ``props_dict`` won't modify ``curve``.
        props_dict['start'] = -1.0
        self.assertNotEqual(curve.start, props_dict['start'])

    def test_subdivide(self):
        klass = self._get_target_class()

        nodes = np.asfortranarray([
            [0.0, 2.0],
            [2.0, 0.0],
        ])
        curve = self._make_one(nodes, nodes)
        left, right = curve.subdivide()

        self.assertIsInstance(left, klass)
        self.assertIs(left.original_nodes, nodes)
        self.assertEqual(left.start, 0.0)
        self.assertEqual(left.end, 0.5)
        expected = np.asfortranarray([
            [0.0, 2.0],
            [1.0, 1.0],
        ])
        self.assertEqual(left.nodes, expected)

        self.assertIsInstance(right, klass)
        self.assertIs(right.original_nodes, nodes)
        self.assertEqual(right.start, 0.5)
        self.assertEqual(right.end, 1.0)
        expected = np.asfortranarray([
            [1.0, 1.0],
            [2.0, 0.0],
        ])
        self.assertEqual(right.nodes, expected)


class TestLinearization(utils.NumPyTestCase):

    NODES = np.asfortranarray([
        [0.0, 0.0],
        [1.0, 1.0],
        [5.0, 6.0],
    ])

    @staticmethod
    def _get_target_class():
        from bezier import _geometric_intersection

        return _geometric_intersection.Linearization

    def _make_one(self, *args, **kwargs):
        klass = self._get_target_class()
        return klass(*args, **kwargs)

    def _simple_curve(self):
        return subdivided_curve(self.NODES)

    def test_constructor(self):
        nodes = np.asfortranarray([
            [4.0, -5.0],
            [0.0, 7.0],
        ])
        curve = subdivided_curve(nodes)
        error = 0.125
        linearization = self._make_one(curve, error)
        self.assertIs(linearization.curve, curve)
        self.assertEqual(linearization.error, error)
        self.assertEqual(
            np.asfortranarray(linearization.start_node),
            np.asfortranarray(nodes[[0], :]))
        self.assertEqual(
            np.asfortranarray(linearization.end_node),
            np.asfortranarray(nodes[[1], :]))

    def test___dict___property(self):
        nodes = np.asfortranarray([
            [0.0, 1.0],
            [0.0, 2.0],
        ])
        curve = subdivided_curve(nodes)
        error = 0.0
        linearization = self._make_one(curve, error)
        props_dict = linearization.__dict__
        # NOTE: We cannot use dictionary equality check because of
        #       the comparison of NumPy arrays.
        self.assertEqual(len(props_dict), 4)
        self.assertIs(props_dict['curve'], curve)
        self.assertEqual(props_dict['error'], error)
        self.assertEqual(props_dict['start_node'], nodes[[0], :])
        self.assertEqual(props_dict['end_node'], nodes[[1], :])
        # Check that modifying ``props_dict`` won't modify ``linearization``.
        props_dict['error'] = 0.5
        self.assertNotEqual(linearization.error, props_dict['error'])

    def test_subdivide(self):
        linearization = self._make_one(self._simple_curve(), np.nan)
        self.assertEqual(linearization.subdivide(), (linearization,))

    def test_start_node_attr(self):
        curve = self._simple_curve()
        linearization = self._make_one(curve, np.nan)
        expected = np.asfortranarray(self.NODES[[0], :])
        self.assertEqual(
            np.asfortranarray(linearization.start_node), expected)
        # Make sure the data is "original" (was previously a view).
        self.assertIsNone(linearization.start_node.base)
        self.assertTrue(linearization.start_node.flags.owndata)

    def test_end_node_attr(self):
        curve = self._simple_curve()
        linearization = self._make_one(curve, np.nan)
        expected = np.asfortranarray(self.NODES[[2], :])
        self.assertEqual(
            np.asfortranarray(linearization.end_node), expected)
        # Make sure the data is "original" (was previously a view).
        self.assertIsNone(linearization.end_node.base)
        self.assertTrue(linearization.end_node.flags.owndata)

    def test_from_shape_factory_not_close_enough(self):
        curve = self._simple_curve()
        klass = self._get_target_class()
        new_shape = klass.from_shape(curve)
        self.assertIs(new_shape, curve)

    def test_from_shape_factory_close_enough(self):
        scale_factor = 2.0**(-27)
        nodes = self.NODES * scale_factor
        curve = subdivided_curve(nodes)
        klass = self._get_target_class()
        new_shape = klass.from_shape(curve)

        self.assertIsInstance(new_shape, klass)
        self.assertIs(new_shape.curve, curve)
        # NODES has constant second derivative equal to 2 * [3.0, 4.0].
        expected_error = 0.125 * 2 * 1 * 5.0 * scale_factor
        self.assertEqual(new_shape.error, expected_error)

    def test_from_shape_factory_no_error(self):
        nodes = np.asfortranarray([
            [0.0, 0.0],
            [1.0, 1.0],
        ])
        curve = subdivided_curve(nodes)
        klass = self._get_target_class()
        new_shape = klass.from_shape(curve)
        self.assertIsInstance(new_shape, klass)
        self.assertIs(new_shape.curve, curve)
        # ``nodes`` is linear, so error is 0.0.
        self.assertEqual(new_shape.error, 0.0)

    def test_from_shape_factory_already_linearized(self):
        error = 0.078125
        linearization = self._make_one(self._simple_curve(), error)

        klass = self._get_target_class()
        new_shape = klass.from_shape(linearization)
        self.assertIs(new_shape, linearization)
        self.assertEqual(new_shape.error, error)


@utils.needs_speedup
class Test_reset_curves_workspace(unittest.TestCase):

    @staticmethod
    def _call_function_under_test(workspace_size):
        from bezier import _speedup

        return _speedup.reset_curves_workspace(workspace_size)

    def test_it(self):
        from bezier import _speedup

        size = 5
        return_value = self._call_function_under_test(size)
        self.assertIsNone(return_value)
        self.assertEqual(_speedup.curves_workspace_size(), size)

    @unittest.expectedFailure
    def test_threadsafe(self):
        from bezier import _speedup

        size_main = 3
        self._call_function_under_test(size_main)

        worker = WorkspaceThreadedAccess()
        self.assertIsNone(worker.size1)
        self.assertIsNone(worker.size2)

        size1 = 7
        size2 = 8
        thread1 = threading.Thread(target=worker.task1, args=(size1,))
        thread2 = threading.Thread(target=worker.task2, args=(size2,))
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # This check demonstrates the **broken-ness** of the implementation.
        # The sizes for each thread should be the sizes actually **set** in
        # the given thread and the workspace in the main thread should be
        # unchanged (i.e. should have ``size_main``). What we'll actually
        # observe is ``(size2, size1, size2)``.
        expected = (size1, size2, size_main)
        actual = (
            worker.size1,
            worker.size2,
            _speedup.curves_workspace_size(),
        )
        self.assertEqual(actual, expected)


@utils.needs_speedup
class Test_curves_workspace_size(unittest.TestCase):

    @staticmethod
    def _call_function_under_test():
        from bezier import _speedup

        return _speedup.curves_workspace_size()

    def test_it(self):
        from bezier import _speedup

        size = 5
        _speedup.reset_curves_workspace(size)
        self.assertEqual(self._call_function_under_test(), size)


def subdivided_curve(nodes):
    from bezier import _geometric_intersection

    return _geometric_intersection.SubdividedCurve(nodes, nodes)


def make_linearization(curve, error=None):
    from bezier import _geometric_intersection

    if error is None:
        error = _geometric_intersection.linearization_error(curve.nodes)
    return _geometric_intersection.Linearization(curve, error)


class WorkspaceThreadedAccess(object):

    def __init__(self):
        self.barrier1 = threading.Event()
        self.barrier2 = threading.Event()
        self.barrier3 = threading.Event()
        self.size1 = None
        self.size2 = None

    def event1(self, size):
        from bezier import _speedup

        # NOTE: There is no need to ``wait`` since this is the first event.
        _speedup.reset_curves_workspace(size)
        self.barrier1.set()

    def event2(self):
        from bezier import _speedup

        self.barrier1.wait()
        result = _speedup.curves_workspace_size()
        self.barrier2.set()
        return result

    def event3(self, size):
        from bezier import _speedup

        self.barrier2.wait()
        _speedup.reset_curves_workspace(size)
        self.barrier3.set()

    def event4(self):
        from bezier import _speedup

        self.barrier3.wait()
        # NOTE: There is no barrier to ``set`` since this is the last event.
        return _speedup.curves_workspace_size()

    def task1(self, size):
        self.event1(size)
        self.size1 = self.event4()

    def task2(self, size):
        self.size2 = self.event2()
        self.event3(size)
