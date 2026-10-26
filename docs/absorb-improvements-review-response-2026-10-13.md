The replacement below strengthens the original prompt in four areas: evidence-based discovery, protection of existing fork behavior, bounded implementation, and verifiable installation. It also separates permission to modify source code from permission to replace the installed application, which is an important distinction for a fork holding personal study data.

The prompt is designed for a coding agent with local repository access. No local repository inspection, upstream verification, implementation, or dispatch has been performed here.

## Complete replacement implementation prompt

# Mission: Evidence-Driven Upstream Integration and Study Experience Improvements for Anki Weibao

You are working in the personal Anki fork at:

`/Users/weiwei/code/anki-weibao`

Your mission is to **discover, evaluate, selectively integrate, test, and prepare a safe local update** containing the most valuable compatible improvements from official Anki, maintained forks, add-ons, and adjacent open-source projects.

This is an implementation assignment, not a research-only assignment. However, research must produce a defensible, bounded implementation batch rather than an ever-expanding wishlist.

Optimize for:

1. Reliability and safety of daily studying.
2. Preservation of personal scheduling, review history, notes, media, and profiles.
3. Reviewer responsiveness, correctness, and usability.
4. Mandarin study, pronunciation, capture, and local audio.
5. Maintainability and compatibility with future official Anki updates.
6. Meaningful, observable improvements rather than feature count.

**Success means a small number of worthwhile changes, integrated completely, with reproducible evidence that the existing fork still works.**

Do not equate the newest upstream revision, largest feature set, or highest number of passing tests with the best outcome.

---

## 0. Authority, uncertainty, and operating boundaries

### 0.1 Source-of-truth hierarchy

Use the following hierarchy when evidence conflicts:

1. Explicit safety and authorization constraints in this prompt.
2. Applicable repository instructions, including `AGENTS.md`.
3. Verified current source code, Git state, configuration, and executable behavior.
4. Current official upstream implementations and documentation.
5. Current maintained fork or add-on implementations.
6. Historical integration reports.
7. Unverified issue discussions, proposals, and assumptions.

Do not treat historical reports as evidence that a feature remains absent, present, broken, or compatible today.

Where repository instructions conflict with this prompt, follow the more restrictive safety requirement. For other consequential conflicts, explain the conflict and request a decision instead of silently overriding project policy.

### 0.2 Permission boundaries

You may:

- Inspect repository history, remotes, documentation, and source.
- Fetch remote metadata and commits without changing the working tree.
- Create local implementation changes.
- Build and test in isolated environments.
- Create disposable test profiles and candidate packages.
- Update appropriate project documentation.
- Prepare a candidate local installation and rollback procedure.

You may not, without separate authorization:

- Commit, push, publish, or create a public release.
- Send messages or submit external issues/PRs.
- Install optional paid services or introduce credentials.
- Change the active user's cards, templates, notes, media, scheduling settings, or cloud state.
- Enable experimental scheduling or new due-date behavior for existing cards.
- Rewrite review history.
- Replace the currently installed app environment.
- Alter the privacy or sharing status of the repository.
- Launch destructive migrations against personal data.

**Authorization to implement and package is not authorization to replace the installed application.**

If the installed application must be closed or replaced, finish all independent preparation first, then request the required authorization once.

Do not add `Co-Authored-By` trailers.

Use subagents only when permitted by applicable instructions. Parallel investigation must not create competing modifications to the same working tree.

### 0.3 Protected personal state

The active profile resides under:

`~/Library/Application Support/Anki2`

The installed application is:

`~/Applications/Anki Weibao.app`

The installed environment is:

`~/Library/Application Support/AnkiWeibao/venv`

Treat the active profile, archived originals, and existing installed environment as protected assets.

No test, migration rehearsal, scheduler experiment, or write-capable runtime harness may target the live profile or original archives.

Read-only inspection through the running application is permitted when it does not mutate study state or create unwanted sync activity.

Do not assume that a tool advertised as read-only is actually read-only without checking its behavior.

---

## 1. Establish and preserve the real baseline

Before selecting work, read:

- `AGENTS.md`
- `FORK.md`
- `RELEASE.md`
- `integrations/ABSORPTION.md`
- The dated Outcome section of `integrations/REVIEW-2026-10-08.md`
- `docs/local-setup-2026-10-12.md`
- Relevant build, testing, packaging, and runtime instructions.

Read the unit-testing guide before modifying tests.

Run `just --list` to discover the project's supported workflows. Do not invent recipe names.

### 1.1 Establish working-tree ownership

Inspect:

- Current branch, HEAD, and Git status.
- Configured remotes and their URLs.
- Staged, unstaged, and untracked files.
- Local patches and relevant worktrees.
- Current application and package version information.
- Installed wheel manifests and package provenance.
- Build environment and relevant runtime configuration.
- Current source-to-installed-package relationship.

Identify all pre-existing uncommitted work, especially Qwen TTS changes.

Preserve those changes byte-for-byte unless modification is necessary, justified, and explicitly distinguishable from pre-existing work.

Do not reset, clean, stash-pop, overwrite, or rebase the user's work destructively.

Prefer an isolated integration worktree when feasible, but verify whether uncommitted changes are required for successful builds or behavior. A clean worktree that silently omits required Qwen work is not an acceptable test baseline.

If isolation is impractical, record a reversible baseline and keep implementation changes distinguishable.

### 1.2 Verify the historical October 12 state

The supplied history says:

- The Air-to-Pro mirror was restored locally on October 12, 2026.
- The installed fork reached the deck list.
- The transferred profile contained 48,897 cards, 24,952 notes, and 38 decks.
- Source checks, synthetic Study tools runtime, wheels, installed-copy smoke testing, and Qwen reviewer runtime passed.
- Some unchanged test targets reused earlier stamps.
- The transferred profile had FSRS disabled.
- No AnkiWeb login was configured.
- Native Tingting remained selected in Mandarin templates.

These are historical observations, not guaranteed current facts.

Verify what can safely be verified today.

Do not interpret changed collection counts as corruption without examining legitimate intervening changes.

Do not interpret a successful application launch as proof of collection completeness, scheduling correctness, or audio quality.

### 1.3 Establish a protected-feature inventory

Before editing, trace the current implementations and tests for:

**Scheduling**

- FSRS7 and RWKV scheduling integration.
- Scheduler configuration and persistence.
- Learning and relearning behavior.
- Filtered-deck behavior.
- Review history, Undo, and sync representation.

**Study tools**

- Overview counts and time estimates.
- Reviewer repair markers.
- Repair diffs and protected-field enforcement.
- Stale-write checks.
- Previewed capture with source metadata.
- Local audio capture and media handling.
- Planned-break preview, apply, and Undo.
- Read-only retention comparison.

**Integration and Mandarin**

- AnkiConnect compatibility with an already-installed add-on.
- Official application-version behavior relied on by integrations.
- Chinese-language study features.
- Qwen Mandarin speech in a separate MLX process.
- Speech caching, cancellation, and profile-close cleanup.
- Native Tingting template selections and fallback behavior.

**Previously integrated or deferred features**

- Numeric search.
- Hourly-review backend data.
- Image-occlusion changes.
- Later-only rescheduling.
- Sibling dispersal.

Determine actual current status from code and tests.

Create a baseline matrix recording:

`Capability | Source owner | Current behavior | Evidence | Existing tests | Regression risk`

Do not reproduce the entire matrix in the final answer unless necessary; retain it in the dated outcome report.

---

## 2. Refresh the external evidence

### 2.1 Compare actual source history

Fetch the configured remotes without overwriting local work:

- `origin`
- `upstream`, expected to correspond to `ankitects/anki`
- `jschoreels`, expected to correspond to `JSchoreels/anki`

Verify their actual URLs before trusting those labels.

Compare against the last **verified integrated ancestors**, not merely the dates of previous reports.

Account for:

- Cherry-picks with different hashes.
- Squashed or rebased patches.
- Equivalent implementations.
- Partially absorbed source ranges.
- Reverted upstream behavior.
- Changed dependencies.
- Existing downstream customizations.

Use ancestry, patch comparison, source inspection, and behavioral evidence as appropriate.

Do not assume that a commit absent from the local history represents a missing feature.

### 2.2 Prioritize primary sources

Investigate:

- Official Anki release notes and source.
- Relevant merged and unmerged upstream PRs.
- Issue discussions with reproducible evidence.
- Maintained forks containing distinct implementations.
- Add-ons with relevant workflows.
- Adjacent projects with reusable approaches.

Record source URL, revision or version, retrieval date, license, relevant code location, and relationship to existing fork behavior.

Do not claim an external candidate is maintained merely because its repository has recent activity.

Distinguish a recently updated dependency or README from actively maintained feature code.

### 2.3 Discovery leads, not accepted priorities

Explicitly revisit:

- Later-only rescheduling, historically associated with upstream PR #5764.
- Sibling dispersal ideas from FSRS Helper.
- A possible UI for already-integrated hourly-review data.
- Clanki reviewer or browser performance ideas.
- Yomitan and AnkiConnect capture workflows.
- Chinese Support add-on behavior.
- Local speech and pronunciation workflows.
- Accessibility and keyboard-navigation improvements.

These are leads only.

For every lead, verify whether the relevant behavior is already present, has changed upstream, conflicts with this fork, or would actually improve daily use.

Do not assume an upstream PR number still identifies an unmerged or desirable patch.

### 2.4 Discover additional maintained forks intelligently

Use the official fork network, relevant PR authors, implementation searches, and references from active maintainers.

Search across these capability areas:

- Reviewer and browser performance.
- Search and query correctness.
- Statistics and study planning.
- Accessibility and keyboard navigation.
- Image occlusion and editing.
- Import, export, backup, and media integrity.
- Scheduling correctness and transparency.
- Mandarin input, capture, speech, and pronunciation.
- Recovery from failed or interrupted operations.

Include additional areas only when they address a concrete problem or provide an unusually compelling, low-risk improvement.

For each promising source, inspect actual implementation rather than relying on descriptions or screenshots.

Check licensing and redistribution compatibility before copying code.

Prefer small, independently maintainable integrations over introducing an entire fork's architectural divergence.

### 2.5 Evaluate adjacent projects without scope inflation

Adjacent projects may offer useful patterns for:

- Transactional preview/apply/Undo.
- Cancellation-safe asynchronous work.
- Local model process isolation.
- Media deduplication and caching.
- Incremental rendering or search.
- Source-aware capture.
- Accessibility and error recovery.

An idea is not automatically a candidate for implementation.

Require a specific Anki problem, a credible integration path, and an observable acceptance criterion.

Do not introduce a new framework, model runtime, service, or database merely because it appears modern.

### 2.6 Stop discovery deliberately

Use two discovery passes:

**Pass A: Broad scan**

Identify meaningful upstream changes and a representative range of maintained alternatives.

**Pass B: Targeted verification**

Inspect source, dependencies, licensing, compatibility, and testability for the strongest candidates.

Stop expanding discovery when additional searching is unlikely to displace the best feasible candidates.

As a default budget, aim for a broad scan of approximately 8–12 distinct source families or repositories, followed by deeper inspection of no more than 6–8 candidates.

These are effort budgets, not quotas. Stop earlier if sufficient evidence exists. Expand only for a concrete unresolved dependency or potentially high-impact issue.

Do not spend implementation time building a comprehensive catalogue of the Anki ecosystem.

---

## 3. Build an evidence-backed candidate decision

For each serious candidate, record:

| Field              | Required evidence                                                         |
| ------------------ | ------------------------------------------------------------------------- |
| Problem            | Specific user-visible or correctness gap                                  |
| Current state      | Verified absent, partial, present, or uncertain                           |
| Provenance         | URL, revision, license, original implementation                           |
| Expected benefit   | Concrete daily-study improvement                                          |
| Integration method | Cherry-pick, adaptation, optional integration, or original implementation |
| Dependencies       | Required upstream code, migrations, packages, configuration               |
| Conflicts          | Scheduling, Study tools, UI, audio, integrations                          |
| Risk               | Data, regression, performance, maintenance                                |
| Validation         | Automated and manual observable checks                                    |
| Decision           | Implement, defer, reject, or already present                              |

Deduplicate equivalent implementations and common ancestry.

### 3.1 Evaluate on separate dimensions

Judge candidates by:

1. User benefit and frequency of use.
2. Correctness and data-safety implications.
3. Quality of implementation evidence.
4. Compatibility with this fork.
5. Regression and migration risk.
6. Ongoing maintenance burden.
7. Ability to verify completion.
8. Dependency and packaging cost.

Do not collapse these into a misleading single score.

A safety-critical fix can outrank a more visible feature even when the visible feature appears more exciting.

A feature that is attractive but difficult to verify may be better deferred.

### 3.2 Resolve consequential assumptions

Explicitly challenge these assumptions:

- Newer upstream code is always better.
- A merged upstream fix can be transplanted independently.
- FSRS Helper behavior belongs inside the scheduler.
- A read-only statistics feature has no data or performance consequences.
- A working backend automatically justifies a new UI.
- A fork's speed improvement will transfer to this architecture.
- More Mandarin audio engines improve the user experience.
- A passing synthetic test proves compatibility with the active profile.
- A successful wheel build proves the installed app uses those bytes.
- A clean launch proves the update is ready for daily study.

Document only the assumptions that materially affect decisions.

### 3.3 Separate adoption strategies

Prefer, in order where appropriate:

1. Existing implementation already satisfies the need: verify and retain.
2. Compatible upstream fix: integrate with minimal divergence.
3. Small adaptation of maintained code: preserve provenance and semantics.
4. Optional add-on integration: avoid duplicating an established extension.
5. Small first-party implementation: use when it reduces operational friction or resolves a demonstrated gap.
6. Large architectural change: defer unless necessary to fix a serious problem.

Do not turn add-on inspiration into unnecessary first-party code.

---

## 4. Select a bounded implementation batch

Choose **at most five changes**, with a default target of two or three coherent improvements.

A change may include required supporting tests, documentation, and narrowly scoped compatibility fixes. Do not disguise unrelated features as dependencies.

Prefer a batch that can be fully implemented, packaged, and validated during this assignment.

### 4.1 Batch selection rules

Prioritize:

- Data integrity or correctness fixes.
- High-frequency reviewer improvements.
- Proven responsiveness improvements.
- Small Mandarin workflow improvements.
- Compatibility fixes needed to preserve current features.
- Low-risk usability improvements using existing backend capabilities.

Do not prioritize merely because a candidate was named in the original prompt.

A candidate must have:

- A verified gap.
- A concrete implementation plan.
- Known dependency and conflict boundaries.
- A rollback or disablement strategy when applicable.
- An observable acceptance test.

If a change cannot meet these conditions, defer it.

### 4.2 Special rules for scheduling changes

Treat scheduling as a higher-risk subsystem.

Before adopting later-only rescheduling, sibling dispersal, or similar behavior, determine:

- Whether it changes persisted scheduling state.
- Whether it changes only presentation or selection behavior.
- Whether it interacts with FSRS7, RWKV, or standard scheduling.
- Whether it requires a collection or configuration migration.
- Whether it affects Undo or review history.
- Whether it changes sync representation.
- Whether it changes behavior for filtered decks, learning, or relearning.

Prefer explicit, disabled-by-default configuration for new scheduling behavior when appropriate.

Do not activate new scheduling features on the user's profile.

Do not implement a partial scheduler change merely because its UI appears straightforward.

### 4.3 Special rules for hourly-review UI

Verify the backend's actual semantics first.

Determine:

- What constitutes an hourly bucket.
- Whether times are local or UTC.
- How daylight-saving transitions are handled.
- Whether data is cached or recomputed.
- Whether statistics include deleted or filtered records.
- Whether the proposed display is read-only.
- Whether it scales to large review histories.

Implement a UI only if it provides meaningful insight and does not duplicate existing statistics.

### 4.4 Special rules for Mandarin speech

Preserve Qwen's process isolation and native Tingting selections.

Do not replace template voices automatically.

Any audio improvement must preserve:

- Correct voice routing.
- Cancellation on rapid reviewer transitions.
- Cache identity and invalidation.
- Process cleanup on profile close.
- Recovery from unavailable local models.
- Native speech fallback.
- Absence of unintended network requests.

Distinguish technical playback success from human pronunciation quality.

### 4.5 Batch decision checkpoint

Before implementation, write a concise internal decision record containing:

- Selected changes.
- Expected observable benefits.
- Source revisions.
- Dependencies and conflicts.
- Explicit exclusions.
- Planned tests.
- Conditions that would stop or defer a change.

Proceed automatically with changes that remain within authorization.

Ask for a decision only when a consequential product choice or permission is genuinely missing.

---

## 5. Implement with minimal divergence

Use existing project architecture, conventions, and recipes.

Prefer changes that can be reviewed independently.

For each selected change:

1. Capture the pre-change behavior.
2. Identify the correct owning code.
3. Implement the complete behavior.
4. Add or update focused tests.
5. Exercise the actual user interaction.
6. Check adjacent regressions.
7. Record upstream provenance and deviations.
8. Verify packaging implications.

Avoid broad refactoring unless required by the selected implementation.

Do not silently modify unrelated Study tools or Mandarin behavior.

### 5.1 Preserve protected invariants

The following must remain functional:

- FSRS7/RWKV scheduling integration.
- Existing reviewer and Study tools entry points.
- Repair markers and protected fields.
- Stale-write rejection.
- Capture preview and source metadata.
- Planned-break preview/apply/Undo.
- Read-only retention comparison.
- AnkiConnect's handling of an already-installed add-on.
- Official application-version behavior relied on by integrations.
- Qwen MLX process isolation and cleanup.
- Native Tingting template configuration.

Create focused regression tests where existing coverage is insufficient.

### 5.2 Handle migrations and compatibility

For changes touching persisted state:

- Identify schema and version implications.
- Validate old-to-new behavior using disposable copies.
- Test interrupted or failed operations where practical.
- Verify rollback limitations.
- Avoid irreversible migrations unless separately authorized.
- Do not assume older binaries can safely open data modified by newer code.

For new optional behavior, prefer safe defaults and explicit configuration.

### 5.3 Preserve source attribution

Record:

- Original project and URL.
- Exact source revision.
- License obligations.
- Local adaptations.
- Upstream tracking considerations.

Do not remove required copyright or attribution notices.

---

## 6. Verification must demonstrate behavior

Use project-supported `just` recipes and the documented test workflow.

Run required `just check`.

A green aggregate result is necessary but not sufficient.

### 6.1 Freshness and reproducibility

Distinguish:

- Fresh tests run against current source.
- Cached or stamp-reused tests.
- Tests not run.
- Tests that failed.
- Tests that were skipped because of environmental limitations.

For modified subsystems, force fresh execution of relevant test slices when feasible.

Do not describe reused stamps as fresh validation.

### 6.2 Behavioral acceptance

Verify relevant workflows through the existing runtime/e2e harness.

Examples include:

**Reviewer**

- Enter and leave review mode.
- Answer and Undo.
- Keyboard shortcuts.
- Reviewer state transitions.
- Rapid card changes.
- Reviewer repair markers.

**Study tools**

- Overview data rendering.
- Repair diff preview.
- Protected-field enforcement.
- Stale-write rejection.
- Capture preview and cancellation.
- Planned-break preview/apply/Undo on disposable data.
- Retention comparison without writes.

**Mandarin**

- Native Tingting routing remains intact.
- Qwen playback on a disposable test case.
- Rapid cancellation.
- Cache hit/miss behavior.
- Process termination on profile close.
- Missing-model or unavailable-engine fallback.

**Integration**

- Existing AnkiConnect add-on is respected.
- No duplicate service or conflicting registration.
- Application-version compatibility remains intact.
- Relevant capture workflows function without unintended writes.

### 6.3 Scheduling test matrix

If scheduling code changes, cover applicable combinations of:

- Standard scheduling.
- FSRS7.
- RWKV.
- Learning.
- Relearning.
- Filtered decks.
- Sibling behavior.
- Undo.
- Sync serialization.
- Existing and newly created cards.
- Disabled-by-default settings.

Use synthetic collections or disposable copies only.

If comprehensive scheduling validation is not feasible, defer the scheduling change rather than presenting partial coverage as sufficient.

### 6.4 Performance evidence

For claimed performance improvements:

- Define the relevant operation.
- Use representative synthetic data.
- Compare baseline and candidate under comparable conditions.
- Include warm-up and repeated runs where meaningful.
- Report median and variability rather than a single favorable run.
- Inspect memory or responsiveness when relevant.
- Check that speed gains do not remove functionality.

The historical profile size can inform representative test scale, but must not justify modifying the live collection.

Do not claim an improvement if results are inconclusive.

### 6.5 Failure and recovery evidence

Exercise applicable negative cases:

- Stale writes.
- Invalid or missing media.
- Interrupted capture.
- Cancelled speech.
- Failed model process.
- Failed package installation.
- Missing optional dependency.
- Failed profile opening.
- Incompatible persisted state.

Verify that failures are visible, recoverable, and do not silently corrupt data.

---

## 7. Build, package, and stage the local update

Use documented project recipes for wheel building, packaging, and installation preparation.

### 7.1 Prove artifact provenance

Record:

- Source HEAD and dirty-tree status.
- Included uncommitted source modifications.
- Build command and environment.
- Produced wheel names and hashes.
- Relevant package manifests.
- Candidate application version.
- Installed candidate package identities.

Verify that the candidate artifacts actually contain the intended changes.

Do not assume a successful build guarantees that the launcher imports those packages.

### 7.2 Test in isolation

Before touching the installed environment:

- Create a separate candidate environment.
- Install candidate artifacts there.
- Launch using a disposable profile.
- Verify application startup.
- Verify reviewer and Study tools behavior.
- Verify AnkiConnect behavior.
- Verify applicable Mandarin audio behavior.
- Verify packaging and resource paths.

Do not point the candidate runtime at the active profile.

### 7.3 Prepare rollback

Before an authorized installed replacement:

- Identify the exact current installed environment.
- Prepare a rollback copy preserving required metadata and permissions.
- Verify the rollback copy is complete enough to restore.
- Record the rollback location and restoration steps.
- Determine whether the candidate introduces non-reversible data changes.

Do not treat a copied directory as a verified rollback without checking its contents and restoration feasibility.

### 7.4 Installation authorization gate

The default outcome is a **validated, staged candidate**.

Once preparation and isolated validation are complete:

- If the installed app is running, request that it be closed.
- Request authorization to replace the installed environment.
- Do not proceed until authorization is granted.
- Preserve the rollback copy during replacement.
- Stop at sign-in or password prompts.

If authorization is not available, leave the existing installation untouched and report the candidate as ready for installation.

If authorization is granted, install using the project's supported procedure.

### 7.5 Post-install verification

After an authorized installation, verify:

- The real launcher opens.
- The expected package versions and hashes are loaded.
- The app reaches the deck list using an approved safe inspection method.
- Study tools are available.
- AnkiConnect integration is intact.
- Applicable speech engines load correctly.
- Native Tingting remains selected.
- No unexpected cloud login or sync action occurred.

Avoid opening the live profile with a potentially incompatible build until compatibility has been established.

Do not run write-capable validation against the live collection.

---

## 8. Documentation and evidence

Update:

- `RELEASE.md` for user-visible changes.
- The current owning documentation for changed behavior.
- Relevant integration provenance records.
- Build or installation instructions only where changed.

Preserve historical reports as historical records.

Do not rewrite older reports to make them appear to describe the current implementation.

Create a dated outcome report in the project's established documentation location, using existing naming conventions.

The report must include:

### A. Baseline

- Current branch and source state.
- Uncommitted work preserved.
- Installed baseline.
- Relevant historical claims verified or corrected.

### B. Discovery

- Source families investigated.
- Candidate comparison.
- Exact URLs and revisions.
- License and dependency findings.
- Deduplicated upstream changes.

### C. Selected implementation

- Changes made.
- Why each was selected.
- Source provenance.
- Files and subsystems affected.
- Conflicts resolved.
- Deferred or rejected alternatives.

### D. Verification

- Fresh test results.
- Reused stamps.
- Runtime/e2e evidence.
- Scheduling matrix where applicable.
- Speech and integration results.
- Performance measurements where applicable.
- Known failures and limitations.

### E. Packaging and installation

- Artifact identities and hashes.
- Source-to-package verification.
- Isolated candidate results.
- Installed state, if authorized.
- Rollback location and restoration procedure.

### F. Remaining gates

- Required authorization.
- Human pronunciation acceptance.
- Any unresolved regression or compatibility concern.
- Clearly bounded next steps.

---

## 9. Stop conditions and recovery

Stop the affected operation if:

- Personal collection integrity may be at risk.
- An operation would overwrite uncommitted work.
- Required licensing cannot be satisfied.
- An unexpected migration would touch live data.
- A scheduling change cannot be validated adequately.
- Package provenance cannot be established.
- An installation cannot be rolled back safely.
- Required authorization is missing.
- A password, credential, or sign-in prompt appears.

Stop only the affected workstream when safe independent work can continue.

If a candidate fails, revert only the changes owned by this assignment, preserving pre-existing work.

Do not force a feature into the batch simply to meet an arbitrary count.

A smaller, fully verified update is preferable to a larger, partially validated one.

---

## 10. Definition of done

The assignment is complete at the appropriate authorization boundary when:

- The current baseline and uncommitted work are documented.
- Current upstream and fork evidence has been refreshed.
- Previously integrated features have been checked for duplication.
- A bounded batch has been selected and justified.
- Selected changes are implemented completely.
- Protected behavior has focused regression coverage.
- Required checks pass or failures are explicitly disclosed.
- Modified test slices have fresh validation.
- Candidate wheels and packaged source are verified.
- The candidate passes isolated runtime checks.
- A usable rollback plan exists.
- Documentation and the dated outcome report are complete.
- Installation occurs only if separately authorized.
- Human acceptance is not claimed without human testing.

If no external candidate survives the evidence and safety requirements, do not manufacture work. Deliver a verified baseline, a reasoned no-change decision, and any narrowly justified correctness or test-coverage improvements that fit the mission.

---

## 11. Final response format

Keep the final response concise, but evidence-rich.

Use these sections:

**1. Implemented**

- Actual changes, source links, and user-visible effects.

**2. Validation**

- Fresh tests, runtime results, performance evidence, and remaining limitations.

**3. Packaging and installation**

- Candidate or installed version, artifact provenance, installation status, and rollback location.

**4. Not adopted**

- Important candidates deferred, rejected, or found already present, with reasons.

**5. Next gate**

- Exactly one highest-priority required action or authorization, if any.

Clearly distinguish:

- Source implemented.
- Tests passed.
- Candidate packaged.
- Candidate runtime verified.
- Installed application updated.
- Human acceptance completed.

Never collapse these into a generic claim that the update is done.

**Guiding principle:** Improve the fork that actually exists, preserve the study system that already works, and adopt only changes whose benefit, compatibility, and verification justify their future maintenance cost.

## Material changes and tradeoffs

| Change                                           | Why it matters                                                                                                                                                                                 |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Separate installation authorization              | The original prompt could be interpreted as permission to replace the app. The replacement allows implementation and staging, but requires approval before changing the installed environment. |
| Default to 2–3 changes, maximum 5                | Prevents broad ecosystem research from producing an unfinishable integration batch.                                                                                                            |
| Two-pass discovery with an effort budget         | Maintains coverage of upstream, forks, add-ons, and adjacent projects without requiring an exhaustive survey.                                                                                  |
| Protected-feature inventory                      | Makes preservation of Study tools, FSRS7/RWKV, AnkiConnect, and Qwen explicit and testable before integration begins.                                                                          |
| Scheduling-specific safety gates                 | Prevents apparently small scheduling changes from silently altering review history, due dates, or sync behavior.                                                                               |
| Performance and artifact provenance requirements | Replaces vague claims of faster performance or successful packaging with measurable comparisons and identifiable build artifacts.                                                              |
| No-change outcome permitted                      | Prevents the agent from implementing unnecessary features simply because the assignment asks for improvements.                                                                                 |

Two consequential choices deserve particular attention.

First, FSRS7/RWKV compatibility should not be treated as a blanket promise that every new scheduler feature must work with every scheduling mode. The implementation agent should determine whether a proposed feature is compatible, can be safely restricted to supported modes, or should be deferred. This is more maintainable than forcing universal support.

Second, human Mandarin pronunciation acceptance is distinct from automated audio validation. The agent can verify that Qwen launches, caches, cancels, and plays audio correctly, but it cannot conclude that the pronunciation, prosody, or voice quality meets your expectations. That remains a separate acceptance gate.

The overall change is from an open-ended absorb the best Anki improvements assignment to a research-informed, bounded integration cycle with explicit evidence, safety boundaries, and a reproducible result.