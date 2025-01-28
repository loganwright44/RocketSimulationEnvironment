from Quaternion import *
from Integrator import *
from VectorPlotter import *
from Design import *
from Element import *
from Builder import *
from ElementTypes import *
from MotorManager import *
from ThrustVectorController import *


def demoSim():
  motor = MotorManager(motor="F15")
  tvc = ThrustVectorController(motor_manager=motor)
  
  data_dict = {
    "body_tube": ConfigDict(
      Type=Tube,
      Args=TubeDictS(inner_radius=0.072, outer_radius=0.074, height=0.8, mass=0.42, is_static=True)
    ),
    "nose_cone": ConfigDict(
      Type=Cone,
      Args=ConeDictS(radius=0.074, height=0.2, mass=0.08, is_static=True)
    ),
    "flight_computer": ConfigDict(
      Type=Cylinder,
      Args=CylinderDictS(radius=0.072, height=0.12, mass=0.18, is_static=True)
    )
  }
  
  motor_idx = len(data_dict)
  
  # let the motor manager produce the data for us and add it to the constraints dictionary
  data_dict.update(motor.getElementData())
  builder = Builder(data_dict=data_dict)
  design, part_numbers = builder.generate_design()
  
  # make sure the motor and the tvc are lined up, the tvc has a specific function to do this which must be performed
  design.manipulate_element(part_numbers["rocket_motor"], np.array([0, 0, -0.4]))
  tvc.moveToMotor(offset=np.array([0, 0, -0.4]))
  
  design.manipulate_element(part_numbers["nose_cone"], np.array([0, 0, 0.4]))
  design.manipulate_element(part_numbers["flight_computer"], np.array([0, 0, 0.15]))
  
  t = 0.0
  tFinal = 4.0
  dt = 1e-2
  
  N = 0
  
  u = Vector(elements=(0, 0, 1))
  
  r_list = []
  omega_list = []
  
  # consolidate the static elements to prepare for simulation loop
  design.consolidate_static_elements()
  
  while t < tFinal:
    N += 1
    r = design.r
    v = design.v
    q = design.q
    omega = design.omega
    
    r_list.append(rotateVector(q=q, v=u))
    omega_list.append(omega)
    
    mass, cg, inertia_tensor = design.get_temporary_properties()

    inertia_tensor_inv = np.linalg.inv(inertia_tensor)

    F, M = tvc.getThrustVector(t=t, cg=cg)

    # use the conjugate quaternion to rotate from body frame to world frame - both vectors are computed in body centered frame initially
    F = rotateVector(q=design.q.get_conjugate(), v=Vector(elements=(F[0], F[1], F[2])))
    M = rotateVector(q=design.q.get_conjugate(), v=Vector(elements=(M[0], M[1], M[2])))

    F = np.array([F[0], F[1], F[2]])
    M = np.array([M[0], M[1], M[2]])

    M = M
    F = F - mass * np.array([0.0, 0.0, 9.8]) # simple gravity force term pulls down on rocket in inertial-frame z direction

    alpha = np.matmul(inertia_tensor_inv, M - np.cross(a=omega.v, b=np.matmul(inertia_tensor, omega.v)))
    alpha = Vector(elements=(alpha[0], alpha[1], alpha[2]))

    a = F / mass
    a = Vector(elements=(a[0], a[1], a[2]))

    q, omega = solver(omega=omega, alpha=alpha, q=q, dt=dt, display=False)

    # add position increment first, then velocity increment next
    r += v * dt
    v += a * dt

    design += KinematicData(
      R=r,
      V=v,
      Q=q,
      OMEGA=omega
    )

    design.step(dt=dt) # reduce the mass of the dynamic elements according to their specs
    tvc.step(dt=dt)
    
    design.dynamic_elements[motor_idx][1] = tvc.getAttitude() # rotate the motor mass to the attitude determined by the servo outputs

    # compute error in orientation - ideally non-zero in a real situation, but the error is computed with yaw-pitch-roll angle differences
    tvc.updateSetpoint(targetx=0.0, targety=0.0)

    t += dt
  
  plotVectors(N=N, vectors=r_list, axes_of_rotation=omega_list, dt=dt)
  
  print("Done")


__all__ = [
  "demoSim"
]