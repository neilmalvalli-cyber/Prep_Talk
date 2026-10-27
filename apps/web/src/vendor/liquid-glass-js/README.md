# Liquid Glass JS

Source: https://github.com/dashersw/liquid-glass-js
Pinned commit: 78cb6ccb0b9987bb60a88b14ccbd13a9e6e8ab2a
License: MIT (see LICENSE).

container.js is the upstream source with one addition: an ES-module default export.

LiquidGlass.tsx adapts Container for React. It replaces document capture with a local
Canvas2D decorative material, uses event-driven rendering, and releases WebGL resources
on unmount. This avoids html2canvas, cached personal content and unmanaged scroll loops.
The upstream shape-aware refraction, blur and masking are retained. The adapter adds
an orb-only Fresnel transparency pass to the final shader output.
Native DOM buttons and text remain above the decorative canvas. WebGL failure falls
back to the existing CSS surfaces; reduced motion and voice state styling remain active.
