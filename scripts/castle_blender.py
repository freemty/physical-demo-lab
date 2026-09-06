"""Build the fixed castle from its shared blueprint; run with Blender 4.5."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector, Quaternion

LAYOUTS = ("Goal", "Loose", "Exploded")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def position(src, mode):
    pos = list(src.get("target_pos", src["pos"]))
    if src.get("free"):
        if mode == "Loose":
            pos = list(src["pos"])
        elif mode == "Exploded":
            pos[2] += .012 * (1 + src["assembly_index"] // 4)
    return pos


def generate(spec, output, render=False):
    materials = {}
    def material(rgba):
        key = tuple(rgba)
        if key not in materials:
            mat = bpy.data.materials.new("Finish_" + str(len(materials)))
            mat.diffuse_color = rgba
            mat.use_nodes = True
            node = mat.node_tree.nodes.get("Principled BSDF")
            node.inputs["Base Color"].default_value = rgba
            node.inputs["Roughness"].default_value = .5
            materials[key] = mat
        return materials[key]

    # This script runs in a new factory-startup background process only.
    goal = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for other in list(bpy.data.scenes):
        if other != goal:
            bpy.data.scenes.remove(other)
    goal.name = "Goal"
    scenes = [goal] + [bpy.data.scenes.new(name) for name in LAYOUTS[1:]]
    for scene in scenes:
        bpy.context.window.scene = scene
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 1.
        scene["preview_only"] = True
        scene["ir_sha256"] = sha(output / "scene_spec.json")
        for src in spec["objects"]:
            parent = bpy.data.objects.new(scene.name + "/" + src["name"], None)
            scene.collection.objects.link(parent)
            parent.location = position(src, scene.name)
            parent["source_name"] = src["name"]
            parent["free_body"] = bool(src.get("free"))
            parent["source_geometry_count"] = len(src["geoms"])
            parent.rotation_mode = "QUATERNION"
            parent.rotation_quaternion = Quaternion(src.get("target_quat", src.get("quat", [1,0,0,0])))
            if src.get("free"):
                parent["piece_index"] = src["assembly_index"]
                parent["target_position"] = src["target_pos"]
                parent["loose_position"] = src["pos"]
                parent["supports"] = json.dumps(src["supports"])
            for g in src["geoms"]:
                if g["shape"] == "box":
                    bpy.ops.mesh.primitive_cube_add(size=2)
                    obj = bpy.context.object
                    obj.scale = g["size"]
                elif g["shape"] == "cylinder":
                    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=g["size"][0], depth=2*g["size"][1])
                    obj = bpy.context.object
                else:
                    raise ValueError("Unsupported blueprint geometry: " + g["shape"])
                obj.name = scene.name + "/" + g["name"]
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                obj.parent = parent
                obj.location = g.get("pos", [0,0,0])
                obj.rotation_mode = "QUATERNION"
                obj.rotation_quaternion = Quaternion(g.get("quat", [1,0,0,0]))
                obj["source_geom"] = g["name"]
                obj["collision"] = bool(g.get("collision", True))
                obj["mass_kg"] = float(g.get("mass", 0))
                obj.data.materials.append(material(g["rgba"]))
                if g.get("collision", True):
                    bevel = obj.modifiers.new("Visual-only edge bevel", "BEVEL")
                    bevel.width = .00065
                    bevel.segments = 3
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,spec["table"]["top"]-.0002))
        bpy.context.object.name = scene.name + "/StudioSurface"
        bpy.context.object.data.materials.append(material([.82,.82,.82,1]))
        loose = scene.name == "Loose"
        eye = (-.65,-.95,1.55) if loose else (-.30,-.55,1.24)
        target = Vector((0,0,.82) if loose else (.28,0,.895))
        bpy.ops.object.camera_add(location=eye)
        camera = bpy.context.object
        camera.name = scene.name + "/Camera"
        camera.rotation_euler = (target-camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = 1.15 if loose else (.62 if scene.name=="Exploded" else .55)
        scene.camera = camera
        for pos, energy, size in [((-.2,-.4,2),95,1.1),((.8,.3,1.6),65,.8)]:
            bpy.ops.object.light_add(type="AREA", location=pos)
            light = bpy.context.object
            light.data.energy = energy
            light.data.size = size
            light.rotation_euler = (Vector((.28,0,.9))-light.location).to_track_quat("-Z","Y").to_euler()
        scene.world = bpy.data.worlds.new(scene.name + "/World")
        scene.world.use_nodes = True
        scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.65,.65,.65,1)
        scene.world.node_tree.nodes["Background"].inputs[1].default_value = .45
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 32
        scene.render.resolution_x = 960
        scene.render.resolution_y = 800
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.exposure = -1.
        if render:
            scene.render.filepath = str(output / ("castle-" + scene.name.lower() + ".png"))
            bpy.ops.render.render(write_still=True)
    bpy.context.window.scene = goal
    bpy.data.texts.new("README").write(
        "Castle20: choose Goal, Loose or Exploded in the Scene selector.\n"
        "These are design views, not animated robot trajectories.\n"
        "Isaac imports scene_spec.json, not this .blend file. Both describe the same 20 bodies.\n"
        "Visual bevels and studio lights are not imported as collision geometry.\n"
        "Manual Blender edits are not exported by this quickstart. See GETTING_STARTED.md.\n")
    bpy.data.texts.new("scene_spec.json").write((output/"scene_spec.json").read_text())
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "castle.blend"))


def verify(spec, output):
    rows = []
    def close(a, b):
        return len(a) == len(b) and max(abs(float(x)-float(y)) for x,y in zip(a,b)) < 1e-6
    assert set(s.name for s in bpy.data.scenes) == set(LAYOUTS), "Unexpected layout scenes"
    assert bpy.data.texts["scene_spec.json"].as_string() == (output/"scene_spec.json").read_text()
    for mode in LAYOUTS:
        scene = bpy.data.scenes[mode]
        parents = {o["source_name"]:o for o in scene.objects if "source_name" in o}
        assert set(parents) == {o["name"] for o in spec["objects"]}
        assert sum(bool(o["free_body"]) for o in parents.values()) == 20
        for src in spec["objects"]:
            parent = parents[src["name"]]
            assert close(parent.location, position(src, mode)), src["name"]
            children = {o["source_geom"]:o for o in parent.children if "source_geom" in o}
            assert set(children) == {g["name"] for g in src["geoms"]}
            for g in src["geoms"]:
                obj = children[g["name"]]
                assert close(obj.location, g.get("pos", [0,0,0]))
                assert close(obj.rotation_quaternion, g.get("quat", [1,0,0,0]))
                assert obj["collision"] == bool(g.get("collision", True))
                assert abs(obj["mass_kg"] - g.get("mass", 0)) < 1e-8
                coords = [v.co for v in obj.data.vertices]
                dimensions = [max(v[k] for v in coords)-min(v[k] for v in coords) for k in range(3)]
                expected = ([2*x for x in g["size"]] if g["shape"] == "box"
                            else [2*g["size"][0],2*g["size"][0],2*g["size"][1]])
                assert close(dimensions, expected), g["name"]
        rows.append({"layout":mode, "independent_parts":20, "geometry_checked":True})
    report = {"success":True, "blender_version":bpy.app.version_string, "layouts":rows,
              "ir_sha256":sha(output/"scene_spec.json"), "blend_sha256":sha(output/"castle.blend"),
              "scope":"Re-opened saved Blender file: source identities, layouts, raw mesh dimensions, local geometry poses, masses and collision labels. Not a physics or robot acceptance."}
    with (output/"blender-audit.json").open("x") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    spec = json.loads(args.spec.read_text())
    if args.verify:
        verify(spec, args.output)
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output/"scene_spec.json").write_bytes(args.spec.read_bytes())
        generate(spec, args.output, args.render)


if __name__ == "__main__":
    main()
