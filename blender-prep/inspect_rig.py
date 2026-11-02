# Read-only Blender-side inspection. Run only through the authorized project flow.
import bpy,json
from collections import Counter
armatures=[]
for o in bpy.context.scene.objects:
 if o.type=='ARMATURE':
  armatures.append({'object':o.name,'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None,'deform':b.use_deform,'head':list(b.head_local),'tail':list(b.tail_local)} for b in o.data.bones],'constraints':[{'bone':b.name,'type':c.type,'target':getattr(getattr(c,'target',None),'name',None),'subtarget':getattr(c,'subtarget',None)} for b in o.pose.bones for c in b.constraints]})
meshes=[]
for o in bpy.context.scene.objects:
 if o.type=='MESH':
  arm=[{'name':m.name,'armature':m.object.name if m.object else None} for m in o.modifiers if m.type=='ARMATURE']
  meshes.append({'object':o.name,'vertices':len(o.data.vertices),'armature_modifiers':arm,'vertex_groups':[g.name for g in o.vertex_groups],'shape_keys':[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],'unweighted_vertices':sum(not v.groups for v in o.data.vertices) if arm else None})
result={'version':bpy.app.version_string,'filepath':bpy.data.filepath,'scene':bpy.context.scene.name,'objects':dict(Counter(o.type for o in bpy.context.scene.objects)),'armatures':armatures,'meshes':meshes,'camera':bpy.context.scene.camera.name if bpy.context.scene.camera else None,'engine':bpy.context.scene.render.engine,'size':[bpy.context.scene.render.resolution_x,bpy.context.scene.render.resolution_y],'actions':[a.name for a in bpy.data.actions]}
# `result` is the connector's read-only return contract. Never print secrets.
