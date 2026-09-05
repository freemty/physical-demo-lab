"""Run the unchanged verified restaurant controller with a visual-only cafe layer."""
from pathlib import Path
import runpy
import sim_runtime


class ShowcaseRun(sim_runtime.Run):
    def camera(self, *args, **kwargs):
        super().camera(*args, **kwargs)
        from restaurant_appearance import RestaurantAppearance
        self.appearance = RestaurantAppearance(self)
        self.appearance.decorate()
        self.appearance.set_shot('loading', emit=False)
        self.saved_shots = set()
        self.capture_shot, self.shot_age = None, 0

    def start(self, metadata):
        metadata = dict(metadata)
        metadata['presentation'] = {
            'entry': 'demos/restaurant_showcase.py', 'baseline_controller': 'demos/restaurant.py',
            'style': 'warm wood cafe with teal upholstery and coral food packaging',
            'lights': {'dome_intensity': 650., 'sun_intensity': 1000., 'sun_rotation_xyz_deg': [35, 15, -15]},
            'shots': self.appearance.SHOTS,
            'physical_properties_unchanged': self.appearance.guard['identical_physical_properties'],
            'new_geometry_collision_free': self.appearance.guard['added_geometry_collision_free'],
            'physics_signature': self.appearance.guard['before_sha256'],
            'scope': 'Decorative package lids, furniture, tableware and plants are visual only; no new interaction claims.',
        }
        super().start(metadata)
        self.event('camera_cut', shot='loading', **self.appearance.SHOTS['loading'])

    def step(self, phase, commands, states_before):
        shot = 'travel' if phase == 'navigate' else 'arrival' if phase == 'final_settle' else 'loading'
        if shot != self.capture_shot:
            self.capture_shot, self.shot_age = shot, 0
        self.shot_age += 1
        self.appearance.set_shot(shot)
        super().step(phase, commands, states_before)
        if self.shot_age >= 12 and shot not in self.saved_shots and (shot != 'loading' or self.step_count >= 400):
            import imageio.v2 as imageio
            frame = self.np.asarray(self.rgb.get_data())
            if frame.ndim == 3:
                imageio.imwrite(self.output/(shot+'.png'), frame[..., :3])
                self.saved_shots.add(shot)


sim_runtime.Run = ShowcaseRun
runpy.run_path(str(Path(__file__).with_name('restaurant.py')), run_name='__main__')
