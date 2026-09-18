# Recorded IQ / transport samples

Place authorized recorded baseband files here for offline pipeline tests, for example:

- `noaa_apt_example.wav` - audio baseband for APT-style workflows
- `meteor_lrpt.iq` - complex IQ captures (document sample rate in a sidecar `.json`)

**Do not commit large binary captures to git.** Keep them local or on USB.

SkyCache simulation mode works without any files in this folder - use `samples/packages/` instead.

Live decode: prefer **SatDump** on the capture, then `skycache ingest` the output package or image.
