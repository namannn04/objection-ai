"use client";

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as THREE from "three";
import { RasterContext } from "@/components/characters/face-parts";
import { HumanPortrait } from "@/components/characters/human";
import { ObjectPortrait, objectMouth } from "@/components/characters/object";
import type { Expression } from "@/components/characters/palette";
import type { CharacterInfo } from "@/lib/types";

export const isHumanChar = (c: CharacterInfo) =>
  c.visual?.kind === "human" || ["judge", "prosecutor", "defense", "reporter"].includes(c.key);

export function mouthAnchor(c: CharacterInfo) {
  return isHumanChar(c)
    ? { x: 100, y: 118, rx: 9, color: "#2b1215", glow: false }
    : objectMouth(c.name, c.visual?.glyph ?? "");
}

const cache = new Map<string, Promise<THREE.Texture>>();

/** Rasterise a character portrait (SVG) into a texture. Mouth omitted when it will be animated in 3D. */
export function portraitTexture(c: CharacterInfo, expression: Expression, withMouth: boolean): Promise<THREE.Texture> {
  const key = `${c.key}|${c.name}|${c.visual?.palette}|${expression}|${withMouth}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const portrait = isHumanChar(c)
    ? createElement(HumanPortrait, { characterKey: c.key, expression, speaking: false, amplitude: null, palette: c.visual?.palette })
    : createElement(ObjectPortrait, {
        name: c.name, glyph: c.visual?.glyph ?? "", paletteName: c.visual?.palette ?? "slate",
        expression, speaking: false, amplitude: null,
      });
  let svg = renderToStaticMarkup(createElement(RasterContext.Provider, { value: { raster: true, mouth: withMouth } }, portrait));
  svg = svg
    .replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="563" ')
    .replace(/var\(--font-geist-mono\),\s*/g, "");
  const p = new Promise<THREE.Texture>((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 563;
      canvas.getContext("2d")!.drawImage(img, 0, 0, 512, 563);
      const tex = new THREE.CanvasTexture(canvas);
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = 4;
      resolve(tex);
    };
    img.onerror = reject;
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  });
  cache.set(key, p);
  return p;
}

function canvasTexture(w: number, h: number, draw: (g: CanvasRenderingContext2D) => void, repeat?: [number, number]) {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  draw(canvas.getContext("2d")!);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  if (repeat) {
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(...repeat);
  }
  tex.anisotropy = 8;
  return tex;
}

/** Marble-ish checker floor: noir black and oxblood tiles with faint veins. */
export function marbleTexture() {
  return canvasTexture(1024, 1024, (g) => {
    const n = 8;
    const s = 1024 / n;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        g.fillStyle = (i + j) % 2 ? "#141011" : "#2a1216";
        g.fillRect(i * s, j * s, s, s);
      }
    }
    g.globalAlpha = 0.07;
    g.strokeStyle = "#f5f0e6";
    for (let k = 0; k < 60; k++) {
      g.lineWidth = Math.random() * 1.5;
      g.beginPath();
      let x = Math.random() * 1024;
      let y = Math.random() * 1024;
      g.moveTo(x, y);
      for (let t = 0; t < 8; t++) {
        x += (Math.random() - 0.5) * 140;
        y += (Math.random() - 0.3) * 90;
        g.lineTo(x, y);
      }
      g.stroke();
    }
    g.globalAlpha = 0.5;
    g.strokeStyle = "#d6ae62";
    g.lineWidth = 2;
    for (let i = 0; i <= n; i++) {
      g.beginPath(); g.moveTo(i * s, 0); g.lineTo(i * s, 1024); g.stroke();
      g.beginPath(); g.moveTo(0, i * s); g.lineTo(1024, i * s); g.stroke();
    }
  }, [3, 3]);
}

/** Walnut paneling with vertical grain. */
export function woodTexture() {
  return canvasTexture(512, 512, (g) => {
    const grad = g.createLinearGradient(0, 0, 512, 0);
    grad.addColorStop(0, "#2a1c14");
    grad.addColorStop(0.5, "#33231a");
    grad.addColorStop(1, "#24170f");
    g.fillStyle = grad;
    g.fillRect(0, 0, 512, 512);
    g.globalAlpha = 0.18;
    for (let i = 0; i < 140; i++) {
      g.strokeStyle = Math.random() > 0.5 ? "#000" : "#5a3d2a";
      g.lineWidth = Math.random() * 2;
      g.beginPath();
      const x = Math.random() * 512;
      g.moveTo(x, 0);
      g.bezierCurveTo(x + 8, 170, x - 8, 340, x + 4, 512);
      g.stroke();
    }
  }, [2, 1]);
}

/** The court seal: rings, ring text and an unbalanced pair of scales. */
export function sealTexture() {
  return canvasTexture(1024, 1024, (g) => {
    g.translate(512, 512);
    g.strokeStyle = "#d6ae62";
    g.fillStyle = "#d6ae62";
    g.lineWidth = 6;
    g.beginPath(); g.arc(0, 0, 490, 0, Math.PI * 2); g.stroke();
    g.lineWidth = 2;
    g.beginPath(); g.arc(0, 0, 465, 0, Math.PI * 2); g.stroke();
    g.beginPath(); g.arc(0, 0, 330, 0, Math.PI * 2); g.stroke();
    const text = "THE COURT OF ABSOLUTE NONSENSE  ·  EST. 2026  ·  ORDER  ·  ";
    g.font = "600 52px ui-monospace, monospace";
    g.textAlign = "center";
    g.textBaseline = "middle";
    const step = (Math.PI * 2) / text.length;
    for (let i = 0; i < text.length; i++) {
      g.save();
      g.rotate(i * step - Math.PI / 2);
      g.translate(0, -400);
      g.fillText(text[i], 0, 0);
      g.restore();
    }
    g.lineWidth = 10;
    g.lineCap = "round";
    g.beginPath(); g.moveTo(0, -200); g.lineTo(0, 210); g.stroke();
    g.beginPath(); g.moveTo(-120, 230); g.lineTo(120, 230); g.stroke();
    g.save(); g.rotate(-0.08);
    g.beginPath(); g.moveTo(-200, -150); g.lineTo(200, -150); g.stroke();
    g.lineWidth = 4;
    for (const x of [-200, 200]) {
      g.beginPath(); g.moveTo(x, -150); g.lineTo(x - 60, -10); g.moveTo(x, -150); g.lineTo(x + 60, -10); g.stroke();
      g.beginPath(); g.moveTo(x - 75, -10); g.quadraticCurveTo(x, 50, x + 75, -10); g.stroke();
    }
    g.restore();
  });
}

/** A brass nameplate / label rendered with the page's loaded fonts. */
export function labelTexture(text: string, opts: { w?: number; h?: number; font?: string; color?: string; bg?: string; border?: string } = {}) {
  const { w = 512, h = 96, font = "600 40px ui-monospace, monospace", color = "#d6ae62", bg = "rgba(9,9,9,0.85)", border = "#d6ae62" } = opts;
  return canvasTexture(w, h, (g) => {
    g.fillStyle = bg;
    g.fillRect(0, 0, w, h);
    g.strokeStyle = border;
    g.lineWidth = 4;
    g.strokeRect(4, 4, w - 8, h - 8);
    g.fillStyle = color;
    g.textAlign = "center";
    g.textBaseline = "middle";
    const label = text.toUpperCase().split("").join(String.fromCharCode(8202));
    // shrink the font until the label fits inside the plate
    let size = Number(/(\d+)px/.exec(font)?.[1] ?? 40);
    g.font = font;
    while (g.measureText(label).width > w * 0.86 && size > 10) {
      size -= 2;
      g.font = font.replace(/\d+px/, `${size}px`);
    }
    g.fillText(label, w / 2, h / 2 + 2);
  });
}

/** Soft radial blob for fake contact shadows and light pools. */
export function radialTexture(inner = "rgba(0,0,0,0.75)", outer = "rgba(0,0,0,0)") {
  return canvasTexture(256, 256, (g) => {
    const grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    grad.addColorStop(0, inner);
    grad.addColorStop(1, outer);
    g.fillStyle = grad;
    g.fillRect(0, 0, 256, 256);
  });
}

/** Light shaft: vertical gradient for additive window beams. */
export function beamTexture() {
  return canvasTexture(64, 512, (g) => {
    const grad = g.createLinearGradient(0, 0, 0, 512);
    grad.addColorStop(0, "rgba(255,232,190,0.55)");
    grad.addColorStop(1, "rgba(255,232,190,0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, 64, 512);
    const side = g.createLinearGradient(0, 0, 64, 0);
    side.addColorStop(0, "rgba(0,0,0,1)");
    side.addColorStop(0.5, "rgba(0,0,0,0)");
    side.addColorStop(1, "rgba(0,0,0,1)");
    g.globalCompositeOperation = "destination-out";
    g.fillStyle = side;
    g.fillRect(0, 0, 64, 512);
  });
}
