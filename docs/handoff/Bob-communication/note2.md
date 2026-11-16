# Note 2: the image permission fix is on main

Your diagnosis in Phase 1 was right. This VM creates files readable by owner and group only, `COPY` keeps those modes, and user 10001 cannot read `/app/src`. It never showed on the Mac, where files are readable by everyone.

The fix is now on `main`: the Dockerfile runs `chmod -R a+rX` on the copied files before `uv sync`. It was reproduced on the Mac with this VM's permissions, and `deploy/verify_image.sh` passes with it.

1. Discard your own Dockerfile change. If it is not committed, run `git restore Dockerfile`. If you committed it, stop and tell Troy before pulling.
2. Run `git pull origin main`. Your `.env` is untracked and is not affected.
3. Rerun Phase 1: `deploy/verify_image.sh` (with `CONTAINER_ENGINE=podman` if needed). Stop after it and report.

From here on, when a file in the repository needs a change, report the problem with the exact error and your proposed fix, and stop. Fixes go onto `main` from Troy's Mac so the deployed image and `main` stay the same. The exceptions are your phase reports, which you write yourself.
