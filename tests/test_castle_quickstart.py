import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import castle
from castle_export import export_keyframes


class EntryTests(unittest.TestCase):
    def test_pinned_blueprint(self):
        self.assertEqual(castle.checked_spec(castle.SPEC), castle.SPEC)
    def test_modified_blueprint_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"spec.json"; p.write_text("{}")
            with self.assertRaises(ValueError): castle.checked_spec(p)
    def test_runtime_not_server_specific(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(castle, "doctor", return_value=0) as probe:
                castle.main(["doctor"])
                self.assertEqual(Path(probe.call_args[0][0].runtime), ROOT/".runtime")
    def test_missing_blender(self):
        with patch("shutil.which", return_value=None):
            with self.assertRaises(ValueError):
                castle.blender_binary(type("Args", (), {"blender":"nonexistent"})())
    def test_build_subprocess_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = type("Args", (), {"blender":"blender","output":str(Path(tmp)/"new"),"threads":2,"render":False})()
            with patch.object(castle, "blender_binary", return_value=Path("/test/blender")):
                with patch("subprocess.run") as run:
                    # A mocked Blender that returns zero but produces no audit must fail.
                    with self.assertRaises((FileNotFoundError, ValueError)):
                        castle.build(args)
    def test_nonpositive_budget_rejected(self):
        with self.assertRaises(SystemExit):
            castle.main(["run","--design","unused","--output","unused","--max-steps","0"])


class ExportTests(unittest.TestCase):
    def fixture(self, root, success=True):
        root.mkdir()
        (root/"source-ir.json").write_text("{}")
        (root/"manifest.json").write_text(json.dumps({"ir_sha256":hashlib.sha256(b"{}").hexdigest()}))
        robot = {"hand_position":[0,0,1],"hand_orientation":[1,0,0,0],"joints":[0]*7}
        command = {"hand_target":[0,0,1],"orientation":[1,0,0,0],"gripper_closed":True}
        rows = [{"step":i,"physics_steps":4*(i+1),"sim_time":(i+1)/60,"phase":p,
                 "commands":[command],"robots":[robot],"objects_after_step":[{"id":"block","position":[0,0,1]}]}
                for i,p in enumerate(["block:lift","block:lift:converge","block:release"])]
        (root/"trajectory.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
        (root/"events.jsonl").write_text(json.dumps({"step":3,"kind":"part_end","name":"block"})+"\n")
        (root/"result.json").write_text(json.dumps({"physics_steps":3,"sim_seconds":3/60,
                                                   "success":success,"completed_parts":["block"] if success else []}))
        return rows
    def test_convergence_merged_and_measured_states_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, out = Path(tmp)/"run", Path(tmp)/"export"
            self.fixture(run)
            report = export_keyframes(run,out)
            self.assertEqual(report["phase_count"],2)
            data = json.loads((out/"keyframes.json").read_text())["segments"]
            self.assertEqual((data[0]["first"]["step"],data[0]["last"]["step"]),(0,1))
            self.assertEqual(data[1]["last"]["robots"][0]["hand_position"],[0,0,1])
            self.assertIn("Not a replay controller",report["scope"])
    def test_failed_run_not_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, out = Path(tmp)/"run", Path(tmp)/"export"
            self.fixture(run,False)
            self.assertFalse(export_keyframes(run,out)["task_reported_success"])
    def test_existing_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                export_keyframes(Path(tmp)/"missing",Path(tmp))
    def test_discontinuous_trace_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, out = Path(tmp)/"run", Path(tmp)/"export"
            rows = self.fixture(run); rows[1]["step"] = 8
            (run/"trajectory.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
            with self.assertRaises(ValueError): export_keyframes(run,out)
            self.assertFalse(out.exists())
    def test_wrong_result_length_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run,out=Path(tmp)/"run",Path(tmp)/"export"; self.fixture(run)
            (run/"result.json").write_text(json.dumps({"physics_steps":999}))
            with self.assertRaises(ValueError): export_keyframes(run,out)
    def test_ir_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run,out=Path(tmp)/"run",Path(tmp)/"export"; self.fixture(run)
            (run/"source-ir.json").write_text("tampered")
            with self.assertRaises(ValueError): export_keyframes(run,out)


if __name__ == "__main__":
    unittest.main()
