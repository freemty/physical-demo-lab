"""Non-colliding cafe presentation layer; no physics or control mutation."""
import hashlib
import json
import math


def linear_color(hex_color):
    values = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]
    return [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values]


def physics_signature(stage):
    """Guard physical schemas, geometry, transforms and physics material bindings."""
    rows = {}
    for prim in stage.Traverse():
        schemas = [str(s) for s in prim.GetAppliedSchemas() if str(s).lower().startswith(('physics', 'physx'))]
        props = {a.GetName(): str(a.Get()) for a in prim.GetAttributes()
                 if a.GetName().startswith(('physics:', 'physx'))}
        rels = {r.GetName(): [str(t) for t in r.GetTargets()] for r in prim.GetRelationships()
                if r.GetName().startswith(('physics:', 'physx')) or r.GetName() == 'material:binding:physics'}
        if schemas or props or rels:
            for attr in prim.GetAttributes():
                if attr.GetName().startswith('xformOp') or attr.GetName() in (
                        'size', 'radius', 'height', 'axis', 'points', 'faceVertexCounts', 'faceVertexIndices'):
                    props[attr.GetName()] = str(attr.Get())
            rows[str(prim.GetPath())] = {'schemas': schemas, 'attributes': props, 'relationships': rels}
    encoded = json.dumps(rows, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest(), rows


class RestaurantAppearance:
    PALETTE = {
        'teal': ('26877E', .44, 0.), 'deep_teal': ('184C49', .50, 0.),
        'wood': ('A66D40', .60, 0.), 'wood_light': ('BA8555', .62, 0.),
        'wood_dark': ('794D31', .64, 0.), 'stone': ('293C39', .38, 0.),
        'cream': ('E8D9BD', .70, 0.), 'white': ('F6F0DF', .28, 0.),
        'metal': ('B6C2C0', .28, .8), 'brass': ('BE9450', .30, .75),
        'black': ('242D2B', .65, 0.), 'coral': ('DC7047', .5, 0.),
        'green': ('3B8050', .58, 0.), 'green_light': ('72A952', .55, 0.),
        'soil': ('453529', .95, 0.), 'tile_a': ('9D9383', .73, 0.),
        'tile_b': ('A79D8C', .73, 0.), 'grout': ('645F55', .85, 0.),
        'coffee': ('422C1F', .18, 0.), 'red': ('C54832', .40, 0.),
        'window': ('60949A', .22, .15),
    }
    SHOTS = {
        'loading': {'eye': [1.65, -1.9, 1.65], 'target': [.33, -.09, .84], 'focal_mm': 27.},
        'travel': {'eye': [4.05, -3.45, 2.8], 'target': [1.28, .53, .65], 'focal_mm': 27.},
        'arrival': {'eye': [3.6, -.3, 1.55], 'target': [2.48, 1.02, .76], 'focal_mm': 32.},
    }

    def __init__(self, run):
        from pxr import Gf, Sdf, UsdGeom, UsdShade
        self.run, self.stage = run, run.stage
        self.Gf, self.UsdGeom, self.UsdShade = Gf, UsdGeom, UsdShade
        self.materials, self.decor_paths, self.shot = {}, [], None
        self.root = '/World/CafeDecor'
        UsdGeom.Xform.Define(self.stage, self.root)
        for name, (color, roughness, metallic) in self.PALETTE.items():
            material = UsdShade.Material.Define(self.stage, '/World/CafeLooks/'+name)
            shader = UsdShade.Shader.Define(self.stage, str(material.GetPath())+'/Surface')
            shader.CreateIdAttr('UsdPreviewSurface')
            shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*linear_color(color)))
            shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(roughness)
            shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(metallic)
            material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
            self.materials[name] = material

    def bind(self, prim, material):
        self.UsdShade.MaterialBindingAPI.Apply(prim).Bind(self.materials[material])

    def _style(self, shape, position, material, scale=None, rotation=None):
        prim = shape.GetPrim()
        xform = self.UsdGeom.Xformable(prim)
        xform.AddTranslateOp().Set(self.Gf.Vec3d(*map(float, position)))
        if rotation:
            xform.AddRotateXYZOp().Set(self.Gf.Vec3f(*map(float, rotation)))
        if scale:
            xform.AddScaleOp().Set(self.Gf.Vec3f(*map(float, scale)))
        self.bind(prim, material)
        self.decor_paths.append(str(prim.GetPath()))
        return prim

    def box(self, path, p, size, material, rotation=None):
        shape = self.UsdGeom.Cube.Define(self.stage, path)
        shape.CreateSizeAttr(1.)
        return self._style(shape, p, material, size, rotation)

    def cylinder(self, path, p, radius, height, material, axis='Z'):
        shape = self.UsdGeom.Cylinder.Define(self.stage, path)
        shape.CreateRadiusAttr(radius)
        shape.CreateHeightAttr(height)
        shape.CreateAxisAttr(axis)
        return self._style(shape, p, material)

    def ellipsoid(self, path, p, radii, material, rotation=None):
        shape = self.UsdGeom.Sphere.Define(self.stage, path)
        shape.CreateRadiusAttr(1.)
        return self._style(shape, p, material, radii, rotation)

    def torus(self, path, p, radius, tube, material, rotation=None):
        points, counts, indices = [], [], []
        n, m = 40, 10
        for i in range(n):
            a = i*2*math.pi/n
            for j in range(m):
                b = j*2*math.pi/m
                r = radius+tube*math.cos(b)
                points.append(self.Gf.Vec3f(r*math.cos(a), r*math.sin(a), tube*math.sin(b)))
        for i in range(n):
            for j in range(m):
                counts.append(4)
                indices.extend([i*m+j, ((i+1)%n)*m+j, ((i+1)%n)*m+(j+1)%m, i*m+(j+1)%m])
        shape = self.UsdGeom.Mesh.Define(self.stage, path)
        shape.CreatePointsAttr(points)
        shape.CreateFaceVertexCountsAttr(counts)
        shape.CreateFaceVertexIndicesAttr(indices)
        shape.CreateSubdivisionSchemeAttr('none')
        return self._style(shape, p, material, rotation=rotation)

    def plant(self, name, x, y, scale=1.):
        path = self.root+'/'+name
        root = self.UsdGeom.Xform.Define(self.stage, path)
        root.AddTranslateOp().Set(self.Gf.Vec3d(x, y, 0))
        root.AddScaleOp().Set(self.Gf.Vec3f(scale))
        self.cylinder(path+'/Pot', [0, 0, .135], .135, .27, 'coral')
        self.torus(path+'/Lip', [0, 0, .27], .131, .012, 'coral')
        self.cylinder(path+'/Soil', [0, 0, .274], .118, .009, 'soil')
        self.cylinder(path+'/Stem', [0, 0, .54], .012, .55, 'wood_dark')
        for i in range(10):
            angle = i*137.5
            a = math.radians(angle)
            z = .40+i*.045
            self.ellipsoid(path+f'/Leaf{i}', [.12*math.cos(a), .12*math.sin(a), z],
                           [.20, .055, .05], 'green' if i%2 else 'green_light', [0, -28, angle])

    def setting(self, name, x, y, z):
        path = self.root+'/'+name
        self.cylinder(path+'/PlateBase', [x, y, z+.004], .079, .007, 'white')
        self.torus(path+'/PlateRim', [x, y, z+.009], .073, .006, 'white')
        self.box(path+'/Napkin', [x-.11, y, z+.004], [.065, .105, .007], 'teal')
        self.box(path+'/ForkHandle', [x-.115, y-.01, z+.010], [.006, .077, .003], 'brass')
        for i in range(3):
            self.box(path+f'/ForkTooth{i}', [x-.121+i*.006, y+.035, z+.010], [.003, .018, .003], 'brass')
        self.cylinder(path+'/Cup', [x+.015, y+.13, z+.035], .031, .065, 'white')
        self.cylinder(path+'/Coffee', [x+.015, y+.13, z+.068], .026, .003, 'coffee')
        self.torus(path+'/CupHandle', [x+.050, y+.13, z+.035], .016, .0045, 'white', [90, 0, 0])

    def label(self, path, text, material='white'):
        # Tiny geometric ink on the negative-Y face; no texture/image dependency.
        glyphs = {
            'B': ['11110','10001','11110','10001','11110'],
            'E': ['11111','10000','11110','10000','11111'],
            'N': ['10001','11001','10101','10011','10001'],
            'T': ['11111','00100','00100','00100','00100'],
            'O': ['01110','10001','10001','10001','01110'],
            'W': ['10001','10001','10101','10101','01010'],
            'A': ['01110','10001','11111','10001','10001'],
            'R': ['11110','10001','11110','10100','10010'],
        }
        pixel = .85/(len(text)*6-1)
        for k, char in enumerate(text):
            for row, cells in enumerate(glyphs[char]):
                for col, value in enumerate(cells):
                    if value == '1':
                        self.box(path+f'/Ink{k}_{row}_{col}',
                                 [-.425+(k*6+col)*pixel, -.506, .14-row*pixel],
                                 [pixel*.82, .006, pixel*.82], material)

    def decorate(self):
        from pxr import UsdLux, UsdPhysics
        before_hash, before = physics_signature(self.stage)
        # Bind visual surfaces, retaining all purpose-specific physics materials.
        existing = {'/World/Floor': 'grout', '/World/Counter': 'stone', '/World/ArmPedestal': 'deep_teal',
                    '/World/DiningTable': 'wood_light', '/World/meal_box': 'coral', '/World/drink_carton': 'teal'}
        for prim in list(self.stage.Traverse()):
            path = str(prim.GetPath())
            if path in existing:
                self.bind(prim, existing[path])
            elif any(path.startswith('/World/'+prefix) for prefix in ('CounterLeg', 'TableLeg', 'ChairBase')):
                if self.UsdGeom.Gprim(prim): self.bind(prim, 'black')
            elif any(path.startswith('/World/'+prefix) for prefix in ('ChairSeat', 'ChairBack')):
                if self.UsdGeom.Gprim(prim): self.bind(prim, 'teal')
            elif path.startswith('/World/ServiceCart/') and self.UsdGeom.Gprim(prim):
                self.bind(prim, 'teal' if path.endswith('Chassis') else 'metal')
        for i in range(10):
            for j in range(8):
                self.box(self.root+f'/Tile{i}_{j}', [-.95+i*.5, -1.25+j*.5, .0005],
                         [.494, .494, .001], 'tile_a' if (i+j)%2 else 'tile_b')
        self.box(self.root+'/BackWall', [1.3, 2.49, 1.25], [5., .045, 2.5], 'cream')
        self.box(self.root+'/LeftWall', [-1.18, .5, 1.25], [.045, 4., 2.5], 'cream')
        self.box(self.root+'/Skirting', [1.3, 2.455, .16], [5., .035, .32], 'deep_teal')
        self.box(self.root+'/CounterCabinet', [.45, -.40, .315], [.80, .46, .62], 'wood_dark')
        for i in range(18):
            self.box(self.root+f'/CounterSlat{i}', [.076+i*.044, -.635, .327],
                     [.033, .025, .587], 'wood' if i%3 else 'wood_light')
        self.box(self.root+'/CounterKick', [.45, -.404, .035], [.81, .47, .07], 'black')
        for i in range(8):
            self.box(self.root+f'/DiningBoard{i}', [2.199+i*.1, 1.49, .751], [.098, .55, .002],
                     'wood_light' if i%3 else 'wood')
        self.setting('PlaceA', 2.42, 1.40, .753)
        self.setting('PlaceB', 2.76, 1.43, .753)
        self.box(self.root+'/BackTableTop', [.65, 1.62, .735], [.82, .55, .05], 'wood_light')
        for i, x in enumerate([.30, 1.0]):
            self.box(self.root+f'/BackTableLeg{i}', [x, 1.62, .355], [.055, .35, .71], 'black')
            self.box(self.root+f'/BackChairSeat{i}', [x, 2.1, .43], [.31, .30, .05], 'teal')
            self.box(self.root+f'/BackChairBack{i}', [x, 2.23, .66], [.31, .045, .45], 'teal')
            for j, yy in enumerate([1.99, 2.21]):
                self.box(self.root+f'/BackChairLeg{i}_{j}', [x, yy, .21], [.23, .028, .42], 'black')
        self.setting('BackSettingA', .46, 1.56, .761)
        self.setting('BackSettingB', .89, 1.59, .761)
        self.plant('PlantLeft', -.72, 2.0)
        self.plant('PlantRight', 3.40, 2.12, 1.2)
        for i in range(3):
            x = .30+i*.60
            self.box(self.root+f'/ArtFrame{i}', [x, 2.45, 1.55], [.42, .03, .58], 'wood_dark')
            self.box(self.root+f'/ArtPaper{i}', [x, 2.427, 1.55], [.385, .008, .545], 'white')
            self.ellipsoid(self.root+f'/ArtLeaf{i}', [x, 2.418, 1.55], [.12, .004, .19],
                           'teal' if i != 1 else 'coral', [0, (i-1)*20, 0])
        self.box(self.root+'/WindowFrame', [2.68, 2.445, 1.60], [1.12, .04, .96], 'wood_dark')
        for i in range(2):
            for j in range(2):
                self.box(self.root+f'/Window{i}{j}', [2.415+i*.53, 2.412, 1.375+j*.45], [.50, .012, .42], 'window')
        for i in range(3):
            self.cylinder(self.root+f'/CounterPlate{i}', [.775, -.32, .707+i*.010], .064, .009, 'white')
        self.box(self.root+'/CuttingBoard', [.17, -.53, .708], [.16, .105, .015], 'wood_light')
        for i in range(3):
            self.ellipsoid(self.root+f'/Tomato{i}', [.14+i*.032, -.52, .730], [.016, .015, .017], 'red')
        # Decorative package skins inherit the original physical Cube transforms.
        self.box('/World/meal_box/LidRim', [0, 0, .515], [1.02, 1.02, .050], 'deep_teal')
        self.box('/World/meal_box/Lid', [0, 0, .55], [.93, .93, .040], 'white')
        self.box('/World/meal_box/LabelBand', [0, -.505, 0], [.95, .010, .46], 'deep_teal')
        self.label('/World/meal_box', 'BENTO')
        roof = self.UsdGeom.Mesh.Define(self.stage, '/World/drink_carton/FoldedTop')
        roof.CreatePointsAttr([self.Gf.Vec3f(*p) for p in [(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5),(-.5,0,.78),(.5,0,.78)]])
        roof.CreateFaceVertexCountsAttr([4,4,3,3])
        roof.CreateFaceVertexIndicesAttr([0,1,5,4,4,5,2,3,0,4,3,1,2,5])
        roof.CreateSubdivisionSchemeAttr('none')
        self.bind(roof.GetPrim(), 'white')
        self.decor_paths.append(str(roof.GetPath()))
        self.box('/World/drink_carton/Seal', [0, 0, .78], [1.0, .05, .04], 'teal')
        self.label('/World/drink_carton', 'WATER')
        for i in range(2):
            wheel = f'/World/CartWheel{i}'
            self.bind(self.stage.GetPrimAtPath(wheel), 'black')
            self.cylinder(wheel+'/Hub', [0, 0, 0], .022, .040, 'metal', axis='Y')
            for j in range(3):
                self.box(wheel+f'/Spoke{j}', [0, (-1 if i else 1)*.018, 0], [.10, .003, .008], 'metal', [0, j*60, 0])
        self.box('/World/ServiceCart/Accent', [.161, 0, 0], [.003, .14, .025], 'brass')
        dome = UsdLux.DomeLight.Get(self.stage, '/World/Light')
        dome.GetIntensityAttr().Set(450.)
        dome.CreateColorAttr(self.Gf.Vec3f(.84, .91, 1.))
        sun = UsdLux.DistantLight.Get(self.stage, '/World/Sun')
        sun.GetIntensityAttr().Set(900.)
        sun.CreateColorAttr(self.Gf.Vec3f(1., .94, .84))
        sun.CreateAngleAttr(1.2)
        after_hash, after = physics_signature(self.stage)
        collision_free = all(not self.stage.GetPrimAtPath(p).HasAPI(UsdPhysics.CollisionAPI)
                             and not self.stage.GetPrimAtPath(p).HasAPI(UsdPhysics.RigidBodyAPI)
                             for p in self.decor_paths)
        self.guard = {'before_sha256': before_hash, 'after_sha256': after_hash,
                      'identical_physical_properties': before == after,
                      'added_geometry_collision_free': collision_free,
                      'decorative_primitive_count': len(self.decor_paths), 'decorative_paths': self.decor_paths}
        self.run.write('visual-physics-guard.json', self.guard)
        if before != after or not collision_free:
            raise RuntimeError('Appearance layer changed physical properties or introduced collision geometry')

    def set_shot(self, shot, emit=True):
        if self.shot == shot:
            return
        config = self.SHOTS[shot]
        camera = self.UsdGeom.Camera.Get(self.stage, '/World/Camera')
        look = self.Gf.Matrix4d().SetLookAt(self.Gf.Vec3d(*config['eye']), self.Gf.Vec3d(*config['target']), self.Gf.Vec3d(0, 0, 1))
        camera.GetOrderedXformOps()[0].Set(look.GetInverse())
        camera.GetFocalLengthAttr().Set(config['focal_mm'])
        self.shot = shot
        if emit:
            self.run.event('camera_cut', shot=shot, **config)
