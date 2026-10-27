# Liquid glass rendering

Fieldnote uses [Liquid Glass JS](https://github.com/dashersw/liquid-glass-js), pinned to commit `78cb6ccb0b9987bb60a88b14ccbd13a9e6e8ab2a`. The MIT-licensed Container implementation is vendored under `apps/web/src/vendor/liquid-glass-js`; its shape-aware refraction, blur and masking shaders are unchanged. The only upstream source addition is an ES-module export. License text ships in `public/third-party-notices.txt`.

`LiquidGlass.tsx` adapts Container to the existing React application. The renderer is used by the interviewer orb, header action, example-question card, voice-control tray and setup summary. Native text, buttons and inputs remain in the DOM above a decorative, pointer-transparent canvas.

For the orb, the adapter adds a Fresnel transparency pass to the shader output: a smoky center, reflective grazing edges and sharp specular highlights. Its refraction uniforms use stronger edge bending and less blur than rectangular surfaces.

The adapter supplies a local Canvas2D material rather than taking the library's default document screenshot. This means the effect refracts the decorative material, not live page text. Resume content, transcripts, passwords and owner keys are never copied into a glass texture. No html2canvas dependency or external CDN request is used.

Rendering is event driven: initial mount, size changes and theme changes. The orb continues to use the existing voice states, audio-level scale and reduced-motion styles. Unmounting cancels queued frames, disconnects observers, removes the library instance, releases shader/buffer/texture resources and loses the WebGL context. Context loss or unavailable WebGL restores the CSS appearance without blocking controls. High-contrast and reduced-transparency preferences suppress the decorative canvas.

Verification: `node evals/check-design.cjs` (with the existing Playwright/Chrome environment variables and the Vite dev server running) checks light/dark themes at four widths and includes `browser-liquid-glass.cjs`. The dedicated glass test verifies rendered pixels and WebGL errors, theme rebuilds, resize behavior, repeated navigation cleanup, native answer input, context-loss fallback and no-WebGL controls. All API data in these checks is synthetic.

The Siri-inspired orb has a dark upper hemisphere, a bright lower caustic and a multicolor internal ribbon. `OrbWaveform.tsx` animates the ribbon only in the speaking state, with amplitude driven by `useVoice.playbackLevel` measured from the received interviewer stream. Microphone RMS stays separate. Stop, disconnect, pause and hidden-page handling clear the playback level. Idle and reduced-motion rendering remain static. Browser checks compare canvas frames during synthetic speech, after stopping and under reduced motion; no physical microphone retest is claimed.
