"""Topology-independent public motion API. Only the humanoid family is implemented.
Future quadruped and winged families supply their own topology, solver and renderer.
They must not reuse biped joint assumptions.
"""
from dataclasses import dataclass
from typing import Callable
@dataclass(frozen=True)
class RigFamily:
 id:str
 evaluate:Callable
 required_joints:tuple
 supported_actions:tuple
class MotionSystem:
 def __init__(self): self.families={}
 def register(self,family):
  if family.id in self.families:raise ValueError('Duplicate rig family')
  self.families[family.id]=family
 def sample(self,character,time,action='walk_turn_thumb'):
  family=self.families[character['rig_family']]
  if action not in family.supported_actions:raise ValueError('Unsupported action for this rig family')
  sample=family.evaluate(character,time)
  missing=set(family.required_joints)-set(sample['joints'])
  if missing:raise ValueError(f'Missing joints: {missing}')
  return {'rig_family':family.id,'action':action,'timestamp':time,**sample}
