# features/clone.py - Clone manager with protocol toggle, queue, editor hook.

import os
import subprocess


def repo_url(repo, protocol="https"):
    """repo: Repo model (or dict). Return clone URL for protocol."""
    clone_url = repo.clone_url if hasattr(repo, "clone_url") else repo.get("clone_url", "")
    ssh_url = repo.ssh_url if hasattr(repo, "ssh_url") else repo.get("ssh_url", "")
    if protocol == "ssh":
        if ssh_url:
            return ssh_url
        return "git@github.com:%s.git" % repo.full_name
    return clone_url or ("https://github.com/%s.git" % repo.full_name)


class CloneManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.queue = []  # list of Repo

    def clone(self, repo, dest_dir=None, protocol=None, on_line=None):
        """Clone repo into dest_dir (default config.clone_dir). Streams stdout.

        Returns (returncode, target_path)."""
        dest_dir = os.path.expanduser(dest_dir or self.cfg.clone_dir)
        protocol = protocol or self.cfg.clone_protocol
        os.makedirs(dest_dir, exist_ok=True)
        url = repo_url(repo, protocol)
        target = os.path.join(dest_dir, repo.name if hasattr(repo, "name") else repo.get("name", ""))
        cmd = ["git", "clone", url]
        proc = subprocess.Popen(
            cmd, cwd=dest_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout or []:
            if on_line:
                on_line(line.strip())
        proc.wait()
        return proc.returncode, target

    def add_to_queue(self, repo):
        if not any(r is repo or getattr(r, "full_name", None) == getattr(repo, "full_name", None)
                   for r in self.queue):
            self.queue.append(repo)

    def run_queue(self, on_status=None):
        """Clone queue sequentially; open editor after each success. Returns list of (repo, ok)."""
        results = []
        while self.queue:
            repo = self.queue.pop(0)
            name = repo.full_name if hasattr(repo, "full_name") else repo.get("full_name", "")
            if on_status:
                on_status("cloning", name)
            code, target = self.clone(repo, on_line=None)
            ok = code == 0
            results.append((repo, ok))
            if ok and self.cfg.editor and os.path.isdir(target):
                self._open_editor(target)
        return results

    def _open_editor(self, path):
        try:
            subprocess.Popen([self.cfg.editor, path])
        except OSError:
            pass
