# Audio and video compatibility

The media expansion adds eight isolated projects and three opt-in combinations.
Both engines build the same public MkDocs configuration in separate environments.
The MkDocs baseline pins `mkdocs-video` 1.5.0 and `mkdocs-audio` 0.0.2.

| Cases | Contracts |
| --- | --- |
| Audio/video defaults | Default iframe/audio rendering, raw HTML, nested paths, and independent activation. |
| Audio/video options and attributes | MIME types, controls, autoplay, loop, muted video, CSS, source overrides, per-element global opt-out, and an option edit during a warm rebuild. |
| Audio/video custom markers | Custom markers, decoded entities, missing sources, unmatched images, and trailing inline text. |
| Audio/video disabled | Marked images remain images until the plugin is enabled during a warm rebuild. |
| Audio-first / video-first | Declaration order decides which plugin owns a shared marker, in both Markdown and raw HTML. |
| Audio + video + minify | Distinct media markers, native controls, valid local sources, and final HTML minification. |

The media extractor compares every media element and its attributes, playback
flags, MIME types, resolved source URLs, ordinary images, explicit content tokens,
and the bytes of local media assets. Publication checks also compare page routes,
canonicals, sitemap membership, and explicit probes. Only style whitespace and
CSS declaration order are normalized; presence and values remain observable.

Every project runs cold and unchanged warm builds. The options and disabled
cases also edit public plugin settings and rebuild without cleaning output.
Generated WAV, WebM, and PNG assets live in `fixtures/media` and are copied into
each independent project by the existing seed mechanism. They contain a short
generated sine wave, solid color frames, and a one-pixel image.

Select the media branch candidate explicitly before its first PyPI release:

```sh
.venv/bin/python -m pytest tests/test_media.py
.venv/bin/python -m pytest tests/test_plugins.py --combinations \
  --zensical-python=/path/to/media-candidate/bin/python \
  --case=plugins/audio/defaults --case=plugins/audio/options-and-attributes \
  --case=plugins/audio/custom-marker --case=plugins/audio/disabled \
  --case=plugins/video/defaults --case=plugins/video/options-and-attributes \
  --case=plugins/video/custom-marker --case=plugins/video/disabled \
  --case=combinations/media/audio-first --case=combinations/media/video-first \
  --case=combinations/media/audio-video-minify
```

HTML and asset comparisons establish generated output compatibility. Browser
playback requires a separate browser check against the generated local files;
these checks do not establish availability or playback of external providers.

The upstream audio plugin emits controls even when `audio_controls` is false.
Both upstream plugins discard text immediately following a replaced image,
including that text in search output. Native honors disabled controls and keeps
the text visible and searchable. Case metadata requires these exact pairs;
unrelated changes, missing embeds, changed attributes, or lost assets still fail.


## Local validation

Validated on macOS on October 5, 2026 against media candidate commit
`4a81e81e78df2a70009f369800280b9feeca5920`, packaged with UI `v0.0.35`.
This is a branch candidate, rather than evidence for a published PyPI release.

- All 11 projects passed with Python 3.11.10 and Python 3.14.6 candidates:
  52 public CLI builds per run, 104 successful builds in total. Every unexpected
  diff is empty; exact intentional differences remain recorded.
- 17 comparator guards passed, together with three existing RSS/minify cases.
- Chromium, Firefox, and WebKit played the generated WAV and WebM files in both
  engines: 12 checks with decoded media and advancing playback time. Controls,
  autoplay and loop properties matched the fixture settings, including the
  known upstream audio-controls difference.
- Ruff, formatting, full case collection, and whitespace checks passed.

The browser smoke check used locally served retained sites. It does not cover
external embed providers, and the hosted Linux/macOS/Windows matrix has not been
rerun with these new cases.
