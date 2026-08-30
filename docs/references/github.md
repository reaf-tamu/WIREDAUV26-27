# Git & GitHub reference

The command-reference side of version control — for the *concepts* (what a repo/commit/branch actually is), see the README's glossary. This doc assumes you know what those words mean and want to know what to actually type, especially now that more than one person is working in this repo at once.

## The golden rule: pull before you start editing

**Every time you sit down to work on this repo — before you open a single file to edit — run:**
```bash
cd ~/auv_ws/src
git pull
```

Why this matters more now than it did when one person had the only copy: with multiple people working on different sensors, someone else may have pushed changes since you last synced. If you start editing a file based on an outdated local copy, you're setting up a conflict (or worse, silently overwriting their work) later, instead of just starting from the current version now. This single habit prevents the large majority of the merge headaches covered later in this doc.

**If `git pull` reports local changes that would be overwritten:** don't ignore this warning or force past it. Commit or stash your own work first, then pull:
```bash
git add -A
git commit -m "WIP: <describe what you're doing>"
git pull
```

## Common commands

| Command | What it does |
|---|---|
| `git status` | Shows what's changed, what's staged, and whether you're ahead/behind the remote. Run this often — it's free, and it's the fastest way to know what state you're actually in before doing anything else. |
| `git pull` | Downloads and merges in whatever's new on GitHub. See above — do this first, every session. |
| `git add <file>` | Stages a specific file's changes to be included in the next commit. |
| `git add -A` | Stages *everything* changed/new/deleted in the whole repo. Convenient, but check `git status` first so you know what you're actually about to include. |
| `git commit -m "message"` | Saves the staged changes as a new commit, with a message describing what changed. |
| `git push` | Uploads your local commits to GitHub, making them visible to everyone else. |
| `git log --oneline -5` | Shows the last 5 commits, one line each — a quick sanity check after a pull/push/merge to confirm what actually landed. |
| `git diff <file>` | Shows exactly what's changed in a file that hasn't been committed yet — always worth a look before committing something you're not 100% sure about. |

### Writing a good commit message

Describe *what changed and why*, specifically enough that someone scanning `git log` later (including future-you) can tell what happened without opening the diff:
- Good: `"Fix VN-100 yaw/pitch sign flip (verified via physical rotation tests)"`
- Not as useful: `"update"`, `"fixes"`, `"more changes"`

You don't need to write an essay — one clear sentence is plenty for most changes.

## Working with multiple people on different sensors

With several people editing different parts of the repo at once, a few habits go a long way toward avoiding conflicts entirely, rather than needing to resolve them after the fact:

- **Pull before you start, every single session** — covered above, worth repeating because it's the single most effective habit here.
- **Commit and push in small, frequent chunks**, rather than making a huge pile of changes over several days before your first commit. A small commit is easy to merge around; a massive one touching a dozen files is much more likely to collide with someone else's work and much harder to untangle if it does.
- **Stay in your own files/packages where possible.** If you're working on the pressure sensor, you're naturally mostly touching `docs/sensors/pressure-sensor.md` and whatever package handles it — genuinely different files from whoever's working on the DVL or on `auv_control`. Different files essentially never conflict, even if commits happen close together in time. Conflicts mainly show up when two people edit the *same lines of the same file*.
- **If you know you're about to touch a shared file** (like `auv_bringup`'s launch file, or a shared message definition in `auv_msgs`) **that someone else might also be touching, say so** — a quick message to the team ("about to edit bringup.launch.py to add the pressure sensor launch") costs nothing and avoids two people fighting over the same lines at the same time.
- **Push reasonably often, don't sit on local commits for days.** The longer a commit sits locally without being pushed, the more likely it's now based on an outdated version of the repo, and the bigger the eventual merge gets.
- **Check `CONTRIBUTING.md` for this team's actual branch/PR conventions** — this doc covers the raw git mechanics that apply either way, but whether a given change should go straight to `main` or through a branch/PR first is a team convention documented there, not something to guess at per-change.

## Merging: what happens, and how to resolve a conflict

### The easy case: no conflict

Most of the time, when you `git pull` and there are new commits from someone else, git merges them in completely automatically — especially if you and they touched different files, or different parts of the same file. You might briefly see an editor open asking for a merge commit message; saving with the default message and closing it (`Ctrl+X`, then `Y`, then `Enter` if it's `nano`) is normally all you need to do.

### The harder case: a real conflict

A conflict happens when git can't automatically tell how to combine two changes — almost always because you and someone else both edited the **same lines** of the **same file**. When this happens, `git pull` will stop partway through and print something like:
```
CONFLICT (content): Merge conflict in vn100_driver/vn100_driver/vn100_ascii_node.py
Automatic merge failed; fix conflicts and then commit the result.
```

**Don't panic, and don't guess-fix it under pressure.** Open the file — git has marked exactly where the conflict is, right inside the file itself:
```python
<<<<<<< HEAD
qx, qy, qz, qw = euler_deg_to_quaternion(-yaw, -pitch, roll)
=======
qx, qy, qz, qw = euler_deg_to_quaternion(yaw, pitch, roll)  # added logging comment here
>>>>>>> origin/main
```

- **`<<<<<<< HEAD`** down to **`=======`** — your local version of these lines.
- **`=======`** down to **`>>>>>>> origin/main`** — the incoming version from GitHub.

Your job is to edit this section into what the file *should* actually say — which might mean keeping your side, keeping theirs, combining both, or writing something slightly different that captures the intent of both changes — and then **delete the `<<<<<<<`, `=======`, and `>>>>>>>` marker lines themselves**. Leaving any of those markers in place means the file is left in a broken, half-conflicted state that won't run correctly, even though git will let you commit it.

Once the file looks correct with no marker lines left:
```bash
git add <the file you just fixed>
git commit
```
(this opens an editor for a merge commit message — save and exit with the default, nothing extra needed)

### If a conflict looks confusing or risky, it's fine to back out

```bash
git merge --abort
```
This cancels the in-progress merge and puts you back to exactly how things were right before you pulled — no conflict markers, nothing half-done. From there, it's fine to stop and ask someone (or ask for help) rather than guessing at a resolution you're not confident about — this is especially true for conflicts in actual code (not just docs), where picking the wrong side can silently reintroduce a bug that was already fixed. We've done exactly this on this project before, when a conflict touched real orientation-correction code rather than plain text.

### A situation worth knowing: "my branch and origin have diverged"

```
Your branch and 'origin/main' have diverged,
and have 2 and 2 different commits each, respectively.
```
This means you have local commits GitHub doesn't have, *and* GitHub has commits you don't have — usually from editing on more than one machine (or someone editing directly on GitHub's web interface) without pulling in between. The fix is the same merge process above:
```bash
git pull
```
and resolve any conflicts it reports using the steps above. This is not a broken or unusual state — it's just git being explicit that both sides moved forward independently and need to be reconciled.

## A note on force-pushing

`git push --force` overwrites whatever's on GitHub with your local history, discarding anything there that you don't have locally. **This is genuinely dangerous with multiple people pushing to the same repo** — if a teammate pushed something after you last pulled, a force-push from you can permanently delete their work with no warning and no easy recovery. Outside of a very specific, deliberate situation (like the one-time initial-setup fix earlier in this project, done when nobody else had cloned the repo yet), avoid `--force` entirely now that multiple people are working here. If you ever hit a situation that seems to call for it, treat that as a sign to stop and ask rather than a normal troubleshooting step.
