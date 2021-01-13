# nuScenes dev-kit. Version 0.1
# Code written by Oscar Beijbom, 2018.
# Licensed under the Creative Commons [see licence.txt]

# from __future__ import annotations

import numpy as np
import math
from enum import IntEnum


class BoxVisibility(IntEnum):
    """ Enumerates the various level of box visibility in an image """
    ALL = 0  # Requires all corners are inside the image.
    ANY = 1  # Requires at least one corner visible in the image.
    NONE = 2  # Requires no corners to be inside, i.e. box can be fully outside the image.
    IN_FRONT = 3  # Requires all corners to be 1 meter front of the camera AND at least one corner be visible in image.


def quaternion_slerp(q0, q1, fraction):
    """
    Does interpolation between two quaternions. This code is modified from
    https://www.lfd.uci.edu/~gohlke/code/transformations.py.html
    :param q0: <np.array: 4>. First quaternion.
    :param q1: <np.array: 4>. Second quaternion.
    :param fraction: <float>. Interpolation fraction between 0 and 1.
    :return: <np.array: 4>. Interpolated quaternion.
    """

    _EPS = np.finfo(float).eps * 4.0
    if fraction == 0.0:
        return q0
    elif fraction == 1.0:
        return q1
    d = np.dot(q0, q1)
    if abs(abs(d) - 1.0) < _EPS:
        return q0
    if d < 0.0:
        # invert rotation
        d = -d
        np.negative(q1, q1)
    angle = math.acos(d)
    if abs(angle) < _EPS:
        return q0
    is_in = 1.0 / math.sin(angle)
    q0 *= math.sin((1.0 - fraction) * angle) * is_in
    q1 *= math.sin(fraction * angle) * is_in
    q0 += q1
    return q0


def view_points(points, view, normalize):
    """
    This is a helper class that maps 3d points to a 2d plane. It can be used to implement both perspective and
    orthographic projections. It first applies the dot product between the points and the view. By convention,
    the view should be such that the data is projected onto the first 2 axis. It then optionally applies a
    normalization along the third dimension.

    For a p

    :param points: <np.float32: 3, n> Matrix of points, where each point (x, y, z) is along each column.
    :param view: <np.float32: n, n>. Defines an arbitrary projection (n <= 4).
        The projection should be such that the corners are projected onto the first 2 axis.
    :param normalize: <bool>. Whether to normalize the remaining coordinate (along the third axis).
    :return: <np.float32: 3, n>. Mapped point. If normalize=False, the third coordinate is the height.
    """

    assert view.shape[0] <= 4
    assert view.shape[1] <= 4
    assert points.shape[0] == 3

    viewpad = np.eye(4)
    viewpad[:view.shape[0], :view.shape[1]] = view

    nbr_points = points.shape[1]

    # Do operation in homogenous coordinates
    points = np.concatenate((points, np.ones((1, nbr_points))))
    points = np.dot(viewpad, points)
    points = points[:3, :]

    if normalize:
        points = points / points[2:3, :].repeat(3, 0).reshape(3, nbr_points)

    return points


def box_in_image(box, intrinsic, imsize, vis_level=BoxVisibility.IN_FRONT):
    """
    Check if a box is visible inside an image without accounting for occlusions.
    :param box: <Box>.
    :param intrinsic: <float: 3, 3>. Intrinsic camera matrix.
    :param imsize: (width <int>, height <int>).
    :param vis_level: <int>. One of the enumerations of <BoxVisibility>.
    :return <Bool>. True if visibility condition is satisfied.
    """

    corners_3d = box.corners()
    corners_img = view_points(corners_3d, intrinsic, normalize=True)[:2, :]

    visible = np.logical_and(corners_img[0, :] > 0, corners_img[0, :] < imsize[0])
    visible = np.logical_and(visible, corners_img[1, :] < imsize[1])
    visible = np.logical_and(visible, corners_img[1, :] > 0)
    visible = np.logical_and(visible, corners_3d[2, :] > 1)

    in_front = corners_3d[2, :] > 1  # True if a corner is at least 1 meter in front of camera.

    if vis_level == BoxVisibility.ALL:
        return all(visible)
    elif vis_level == BoxVisibility.ANY:
        return any(visible)
    elif vis_level == BoxVisibility.NONE:
        return True
    elif vis_level == BoxVisibility.IN_FRONT:
        return any(visible) and all(in_front)
    else:
        raise ValueError("vis_level: {} not valid".format(vis_level))
