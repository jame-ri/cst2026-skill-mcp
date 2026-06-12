# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

""" This module provides 3d coordinate systems to describe the sensor orientation and the respective scan directions
for MIMO RADARs. The coordinate systems have to be specified in order to determinte the scan direction for the angle of
arrival algorithms.
"""

import numpy as np
import numpy.typing as npt
from abc import ABC
from typing import Type

Vector3D = Type[npt.NDArray[np.float64]]


class BasisVectors:
    Xhat: Vector3D = np.array([1, 0, 0])
    Yhat: Vector3D = np.array([0, 1, 0])
    Zhat: Vector3D = np.array([0, 0, 1])
    ZeroVec: Vector3D = np.array([0, 0, 0])


class CoordinateSystem(ABC):
    def get_unit_vector(self, theta: float, phi: float) -> Vector3D:
        """
        Returns unit vector corresponding to parametrization in spherical
        coordinate system.

        Parameters
        ----------
        theta : float
            Theta coordinate of vector in spherical coordinate system
        phi : float
            Phi coordinate of vector in spherical coordinate system

        Returns
        -------
        vec : array(float)
            unit vector
        """
        pass

    def get_vector(self, theta: float, phi: float, r: float) -> Vector3D:
        """
        Returns cartesian vector corresponding to parametrization in spherical
        coordinate system.

        Parameters
        ----------
        theta : float
            Theta coordinate of vector in spherical coordinate system
        phi : float
            Phi coordinate of vector in spherical coordinate system
        r : float
            Radial coordinate of vector in spherical coordinate system

        Returns
        -------
        vec : array(float)
            Input vector reparametrized in cartesian coordinates of
            underlying orthonormal coordinate system ([Uhat, Vhat, What]).
        """        
        pass

    def get_unit_vector_component(self,
                                  i: int,
                                  theta: float,
                                  phi: float) -> float:
        """
        Returns i-th cartesian component of vector given in the
        Elevation-over-Azimuth coordinate system representation by
        (theta_x, theta_y, r)

        Parameters
        ----------
        i : int
            index of component that should be returned
        theta : float
            theta vector component in Elevation-over-Azimuth coordinate system representation
        phi : float
            phi vector component in Elevation-over-Azimuth coordinate system representation

        Returns
        -------
        float
            i-th cartesian component of vector
        """
        pass

    def get_theta_phi_r(self, vec3: Vector3D, phi_0_to_2pi: bool = False):
        """
        Returns the spherical coordinates of a cartesian vector.

        Parameters
        ----------
        vec3 : array(float)
            Cartesian vector
        phi_0_to_2pi : bool
            measuring phi angle from [0,2pi) else [-pi,pi]

        Returns
        -------
        tuple
            Local coordinates (theta, phi, r) of vector vec3
        """
        pass


class SphericalCoordinateSystem(CoordinateSystem):
    """
    Implementation of a spherical coordinate system with orthonormal axis 
    vectors Uhat, Vhat and What.
    Angle "Theta" is defined as the inverse cosine between position vector and
    What-axis, angle "Phi" is defined in plane perpendicular to What-axis.

    .. figure:: /_static/images/radar/KOS_spherical.svg
                :scale: 100%

                Spherical coordinate systems
    """

    def __init__(self,
                 Uhat=BasisVectors.Xhat,
                 Vhat=BasisVectors.Yhat,
                 What=BasisVectors.Zhat,
                 origin=BasisVectors.ZeroVec):
        """
        Parameters
        ----------
        Uhat : array(float)
            first dimension basis vector
        Uhat : array(float)
            second dimension basis vector
        Uhat : array(float)
            third dimension basis vector
        origin : array(float)
            vector of origin of coordinate system with respect to standard
            coordinate systen
        """
        self.Uhat = Uhat
        self.Vhat = Vhat
        self.What = What
        self.origin = origin

    def get_unit_vector(self, theta, phi):
        """
        Returns unit vector corresponding to parametrization in spherical
        coordinate system.

        Parameters
        ----------
        theta : float
            Theta coordinate of vector in spherical coordinate system
        phi : float
            Phi coordinate of vector in spherical coordinate system

        Returns
        -------
        vec : array(float)
            unit vector
        """
        vec = (self.Uhat*np.cos(phi)*np.sin(theta)
               + self.Vhat*np.sin(phi)*np.sin(theta)
               + self.What*np.cos(theta))
        return vec

    def get_vector(self, theta, phi, r):
        """
        Returns cartesian vector corresponding to parametrization in spherical
        coordinate system.

        Parameters
        ----------
        theta : float
            Theta coordinate of vector in spherical coordinate system
        phi : float
            Phi coordinate of vector in spherical coordinate system
        r : float
            Radial coordinate of vector in spherical coordinate system

        Returns
        -------
        vec : array(float)
            Input vector reparametrized in cartesian coordinates of
            underlying orthonormal coordinate system ([Uhat, Vhat, What]).
        """
        vec = self.origin + r*self.get_unit_vector(theta, phi)
        return vec

    def get_unit_vector_component(self, i, theta, phi):
        """
        Returns i-th cartesian component of the unit vector given in the
        spherical coordinate system representation by (theta, phi)

        Parameters
        ----------
        i : int
            index of component that should be returned
        theta : array(float)
            array of theta angles
        phi : array(float)
            array of phi angles

        Returns
        -------
        array(float)
            vector of i-th component
        """
        if i == 0:
            return np.cos(phi)*np.sin(theta)
        elif i == 1:
            return np.sin(phi)*np.sin(theta)
        elif i == 2:
            return np.cos(theta)*np.ones_like(phi)
        else:
            raise IndexError(
                "component index i={} is outside of range".format(i))

    def get_theta_phi_r(self, vec3, phi_0_to_2pi=False):
        """
        Returns the spherical coordinates of a cartesian vector.

        Parameters
        ----------
        vec3 : array(float)
            Cartesian vector
        phi_0_to_2pi : bool
            measuring phi angle from [0,2pi) else [-pi,pi]

        Returns
        -------
        tuple
            Local coordinates (theta, phi, r) of vector vec3
        """
        vec3 = vec3 - self.origin
        r = np.linalg.norm(vec3)
        if (r < 1e-12):  # vec3 is the origin of the coordinate system
            return (0.0, 0.0, 0.0)
        else:
            # project
            u = np.dot(self.Uhat, vec3)
            v = np.dot(self.Vhat, vec3)
            w = np.dot(self.What, vec3)
            theta = np.arccos(w/r)
            if phi_0_to_2pi:
                phi = np.arctan2(v, u)
                phi = phi if phi > 0 else phi + 2*np.pi
            else:
                phi = np.arctan2(v, u)
            return (theta, phi, r)


class ElOverAzCoordinateSystem(CoordinateSystem):
    """
    Elevation-over-Azimuth coordinate system in which the pole is not located
    along the z-axis but along the y-axis. Theta angle is defined as the
    arcsin(v/r). Mind that in the drawing the angle is displayed in the v-w-plane
    , however, it should not be confused as being being defined in this plane.
    Unlike in the case of the sensor coordinate system, where the angles are defined in 
    the respective planes, in the Elevation-Over-Azimuth Coordinate System,
    points of equal angles of Theta will lie along a spherical arc around the
    coordinate origin. Phi angle is defined as the arctan(u/w).

    .. figure:: /_static/images/radar/KOS_ElOverAz.svg
                    :scale: 100%

                    Elevation-over-Azimuth coordinate systems
    """

    def __init__(self,
                 Uhat=BasisVectors.Xhat,
                 Vhat=BasisVectors.Yhat,
                 What=BasisVectors.Zhat,
                 origin=BasisVectors.ZeroVec):
        """
        Parameters
        ----------
        Uhat : array(float)
            first dimension basis vector
        Uhat : array(float)
            second dimension basis vector
        Uhat : array(float)
            third dimension basis vector
        origin : array(float)
            vector of origin of coordinate system with respect to global
            cartesian coordinate system
        """
        self.Uhat = Uhat
        self.Vhat = Vhat
        self.What = What
        self.origin = origin

    def get_unit_vector(self, theta, phi):  # theta is elevation, phi is azimuth
        """
        Returns cartesian vector corresponding to parametrization in
        Elevation-over-Azimuth coordinate system.

        Parameters
        ----------
        theta : float
            Theta coordinate of vector in Elevation-over-Azimuth coordinate
            system
        phi : float
            Phi coordinate of vector in Elevation-over-Azimuth coordinate
            system

        Returns
        -------
        vec : array(float)
            Input vector reparametrized in cartesian coordinates of
            underlying orthonormal coordinate system ([Uhat, Vhat, What]).
        """
        vec = (self.Uhat*np.cos(theta)*np.sin(phi)
               + self.Vhat*np.sin(theta)
               + self.What*np.cos(theta)*np.cos(phi))
        return vec

    def get_vector(self, theta, phi,  r):  # theta is elevation, phi is azimuth
        """
        Returns cartesian vector corresponding to parametrization in
        Elevation-over-Azimuth coordinate system.

        Parameters
        ----------
        theta : float
            Theta coordinate of vector in Elevation-over-Azimuth coordinate
            system
        phi : float
            Phi coordinate of vector in Elevation-over-Azimuth coordinate
            system
        r : float
            Radial coordinate of vector in Elevation-over-Azimuth coordinate
            system

        Returns
        -------
        vec : array(float)
            Input vector reparametrized in cartesian coordinates of
            underlying orthonormal coordinate system ([Uhat, Vhat, What]).
        """
        vec = self.origin + r*self.get_unit_vector(theta, phi)
        return vec

    def get_unit_vector_component(self, i, theta, phi):
        """
        Returns i-th cartesian component of vector given in the
        Elevation-over-Azimuth coordinate system representation by
        (theta_x, theta_y, r)

        Parameters
        ----------
        i : int
            index of component that should be returned
        theta : float
            theta vector component in Elevation-over-Azimuth coordinate system representation
        phi : float
            phi vector component in Elevation-over-Azimuth coordinate system representation

        Returns
        -------
        float
            i-th cartesian component of vector
        """
        if i == 0:
            return np.cos(theta)*np.sin(phi)
        elif i == 1:
            return np.sin(theta)*np.ones_like(phi)
        elif i == 2:
            return np.cos(theta)*np.cos(phi)
        else:
            raise IndexError(
                "component index i={} is outside of range".format(i))

    def get_theta_phi_r(self, vec3):
        """
        Returns the ElOverAzCoordinateSystem coordinates of a cartesian vector.

        Parameters
        ----------
        vec3 : array(float)
            Cartesian vector

        Returns
        -------
        tuple
            Local coordinates (El, Az, r) of vector vec3
        """
        vec3 = vec3 - self.origin
        r = np.linalg.norm(vec3)
        if (r < 1e-12):  # vec3 is the origin of the coordinate system
            return (0.0, 0.0, 0.0)
        else:
            # project
            u = np.dot(self.Uhat, vec3)
            v = np.dot(self.Vhat, vec3)
            w = np.dot(self.What, vec3)
            El = np.arcsin(v/r)  # + np.pi/2
            Az = np.arctan(u/w)  # % np.pi
            # phi = phi if v >= 0 else phi + 2.0*np.pi  # phi in [0,2*pi]
            return (El, Az, r)


class SensorCoordinateSystem1(CoordinateSystem):
    """
    Sensor-Centric Coordinate System in which the antennas extend in the U-V-plane, hence the look ahead normal is
    located along the W-axis. 
    Theta angle is defined as arctan(u/w) in the projection into the U-W-plane.
    Phi angle is defined as arctan(v/w) in the projection into the V-W-plane.

    .. figure:: /_static/images/radar/KOS_sensor.svg
                :scale: 100%

                Sensor coordinate system. 
    """

    def __init__(self,
                 Uhat=BasisVectors.Xhat,
                 Vhat=BasisVectors.Yhat,
                 What=BasisVectors.Zhat,
                 origin=BasisVectors.ZeroVec):
        """
        Parameters
        ----------
        Uhat : array(float)
            first dimension basis vector
        Uhat : array(float)
            second dimension basis vector
        Uhat : array(float)
            third dimension basis vector
        origin : array(float)
            vector of origin of coordinate system with respect to standard coordinate system
        """
        self.Uhat = Uhat
        self.Vhat = Vhat
        self.What = What
        self.UVW = np.vstack([Uhat, Vhat, What])
        self.origin = origin
        self.originUVW = np.array(
            [np.dot(origin, Uhat), np.dot(origin, Vhat), np.dot(origin, What)])

    def get_unit_vector(self, theta, phi):
        """
        Return cartesian vector corresponding to parametrization in Sensor coordinate system.

        Parameters
        ----------
        theta : float
            Theta coordinate of vector in Sensor coordinate system
        phi : float
            Phi coordinate of vector in Sensor coordinate system
        r : float
            Radial coordinate of vector in Sensor coordinate system

        Returns
        -------
        vec : array(float)
            Input vector reparametrized in cartesian coordinates of
            underlying orthonormal coordinate system ([Uhat, Vhat, What]).
        """
        tan2x = np.power(np.tan(theta), 2)
        tan2y = np.power(np.tan(phi), 2)
        z = 1/np.sqrt(1.0 + tan2x + tan2y)
        vec = (self.Uhat*z*np.tan(theta)
               + self.Vhat*z*np.tan(phi)
               + self.What*z)
        return vec

    def get_vector(self, theta, phi, r):
        """
        Return cartesian vector corresponding to parametrization in Sensor coordinate system.

        Parameters
        ----------
        theta : float
            Theta coordinate of vector in Sensor coordinate system
        phi : float
            Phi coordinate of vector in Sensor coordinate system
        r : float
            Radial coordinate of vector in Sensor coordinate system

        Returns
        -------
        vec : array(float)
            Input vector reparametrized in cartesian coordinates of
            underlying orthonormal coordinate system ([Uhat, Vhat, What]).
        """
        vec = self.origin + r*self.get_unit_vector(theta, phi)
        return vec

    def get_unit_vector_component(self, i, theta, phi):
        """
        Returns i-th cartesian component of vector given in the sensor coordinate
        system representation by (theta, phi, r)

        Parameters
        ----------
        i : int
            Index of component that should be returned
        theta : float
            Theta vector component in sensor coordinate system representation
        phi : float
            Phi vector component in sensor coordinate system representation
        r : float
            Radial vector component in sensor coordinate system representation

        Returns
        -------
        float
            i-th cartesian component of vector
        """
        tan2x = np.power(np.tan(theta), 2)
        tan2y = np.power(np.tan(phi), 2)
        z = 1/np.sqrt(1.0 + tan2x + tan2y)
        if i == 0:
            return z*np.tan(theta)
        elif i == 1:
            return z*np.tan(phi)
        elif i == 2:
            return z
        else:
            raise IndexError(
                "component index i={} is outside of range".format(i))

    def get_theta_phi_r(self, vec3):
        """
        Returns the SensorCoordinateSystem1 coordinates of a cartesian vector.

        Parameters
        ----------
        vec3 : array(float)
            Cartesian vector

        Returns
        -------
        tuple
            Local coordinates (theta, phi, r) of vector vec3
        """
        vec3 = vec3 - self.origin
        r = np.linalg.norm(vec3)
        if (r < 1e-12):  # vec3 is the origin of the coordinate system
            return (0.0, 0.0, 0.0)
        else:
            # project
            u = np.dot(self.Uhat, vec3)
            v = np.dot(self.Vhat, vec3)
            w = np.dot(self.What, vec3)
            theta = np.arctan(u/w)
            phi = np.arctan(v/w)
            return (theta, phi, r)


def rotate_vector_3d(u, axis, angle):
    """Rotate 3d vector u around axis with angle in counterclockwise direction"""
    rotated_u = (np.dot(axis, u) * axis
                 + np.cos(angle) * np.cross(np.cross(axis, u), axis)
                 + np.sin(angle) * np.cross(axis, u))
    return rotated_u


def rotate_coordinate_system(coordinate_system, axis, angle, rotate_origin=False):
    """Rotate the U, V, W vectors of a coordinate system and optionally the origin"""
    coordinate_system.Uhat = rotate_vector_3d(
        coordinate_system.Uhat, axis, angle)
    coordinate_system.Vhat = rotate_vector_3d(
        coordinate_system.Vhat, axis, angle)
    coordinate_system.What = rotate_vector_3d(
        coordinate_system.What, axis, angle)
    if rotate_origin:
        coordinate_system.Origin = rotate_vector_3d(
            coordinate_system.origin, axis, angle)
