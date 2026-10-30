import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

import downloader


App = runpy.run_path(str(Path(__file__).resolve().parents[1] / "NOXLAB_DOWNLOADER.pyw"))["DownloaderApp"]


class RuntimeInstallTests(unittest.TestCase):
    def setUp(self):
        self.icons = patch.multiple(App, _apply_window_icon=lambda _: None, _apply_dark_title_bar=lambda _: None)
        self.icons.start()
        self.app = App()
        self.app.withdraw()

    def tearDown(self):
        for callback in self.app.tk.call("after", "info"):
            self.app.after_cancel(callback)
        self.app.destroy()
        self.icons.stop()

    def finish_node(self, result, runtime):
        self.app._start_process_ui("Installing", cancellable=False)
        self.assertTrue(self.app.node_button.instate(["disabled"]))
        self.assertTrue(self.app.stop_button.instate(["disabled"]))
        with patch.object(self.app, "_run_process", return_value=result), patch.object(downloader, "detect_js_runtime", return_value=runtime):
            self.app._run_install_node()
            self.app.update()
        self.assertFalse(self.app.busy)
        self.assertFalse(self.app.node_button.instate(["disabled"]))

    def test_install_success(self):
        self.finish_node(0, "node:C:/Program Files/nodejs/node.exe")
        self.assertIn("Node.js is ready", self.app.status_var.get())

    def test_cancel_does_not_claim_success_when_old_node_exists(self):
        self.finish_node(1, "node:C:/Program Files/nodejs/node.exe")
        self.assertIn("did not finish", self.app.status_var.get())

    def test_completed_installer_requires_detectable_runtime(self):
        self.finish_node(0, None)
        self.assertIn("not detected", self.app.status_var.get())

    def test_repeated_click_cannot_launch_two_installers(self):
        with patch("threading.Thread") as thread:
            self.app.install_node()
            self.app.install_node()
            self.app.start_download()
            self.app.update_engine()
            self.assertEqual(thread.call_count, 1)

    def test_missing_powershell_recovers_controls(self):
        self.app._start_process_ui("Installing", cancellable=False)
        with patch("subprocess.Popen", side_effect=FileNotFoundError("powershell missing")):
            self.app._run_install_node()
            self.app.update()
        self.assertFalse(self.app.busy)
        self.assertIn("powershell missing", self.app.output.get("1.0", "end"))

    def test_permission_error_shows_node_and_admin_advice(self):
        self.app._start_process_ui("Downloading")
        with patch.object(downloader, "build_download_command", side_effect=PermissionError("Access denied")):
            self.app._run_download(downloader.build_parser().parse_args([]))
            self.app.update()
        self.assertFalse(self.app.busy)
        text = self.app.output.get("1.0", "end")
        self.assertIn("Install Node.js LTS", text)
        self.assertIn("Run as administrator", text)

    def test_node_can_be_found_without_refreshed_path(self):
        with patch("shutil.which", return_value=None):
            runtime = downloader.detect_js_runtime("node")
        # This machine already has Node installed; this verifies the registry/standard-folder fallback.
        if not runtime:
            self.skipTest("Node.js is not installed on this machine")
        self.assertTrue(Path(runtime.split(":", 1)[1]).is_file())

    def test_controls_fit_minimum_and_default_window_sizes(self):
        self.app.deiconify()
        for size in ("980x660", "1180x760"):
            self.app.geometry(size)
            self.app.update()
            self.app.update_idletasks()
            for widget in (self.app.download_button, self.app.update_button, self.app.node_button, self.app.stop_button):
                x = widget.winfo_rootx() - self.app.winfo_rootx()
                self.assertGreaterEqual(x, 0)
                self.assertLessEqual(x + widget.winfo_width(), self.app.winfo_width())
                self.assertGreaterEqual(widget.winfo_width(), widget.winfo_reqwidth())


if __name__ == "__main__":
    unittest.main()
