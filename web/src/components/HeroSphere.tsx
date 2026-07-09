import { useFrame, useLoader, type ThreeEvent } from "@react-three/fiber";
import gsap from "gsap";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

// Exit distance is generously larger than the frustum's half-width at this
// camera distance/FOV, so the sphere is fully clear of the visible frame
// well before the 700ms is up, not just mostly off to one side.
const EXIT_X = 14;
const EXIT_DURATION = 0.7; // seconds, within the 600-800ms brief

// Continuous rotation per explicit brief (2026-07-09), replacing the
// earlier sway. Known, flagged risk: the texture is a flat photo, not a
// seamless equirectangular map, so its left/right edges don't line up - a
// full 360deg spin WILL eventually carry that seam through the visible
// horizon slice. Kept slow enough that it's an infrequent, brief moment
// rather than a constant artifact; watch for it directly rather than
// assume it's fine.
const ROTATION_SPEED = 0.05; // rad/sec, one full turn every ~126s

const SPHERE_RADIUS = 5;
// Sphere's resting height - pulled down from -3.85 so the visible arc
// clears the hero copy with margin at common laptop heights (1366x768 was
// measured overlapping by ~11px at the old value). Preserved across every
// glow-treatment revision since it's an independent, separately-verified fix.
const GROUP_Y = -4.35;

const GLOW_COLOR = new THREE.Color("#7CFF3B");

// Main-surface shader: unlit texture sampling like meshBasicMaterial, plus
// two additions that make the surface read as glowing energy rather than a
// flat dark photo with dots on it:
//   1) a brightness boost on the sharp sample itself (bright pixels pushed
//      further; near-black background stays near-black, since out*boost
//      stays near 0 when out is near 0);
//   2) blending in a second, PRE-blurred copy of the same texture (built
//      once at load time, see makeBlurredTexture below) additively, so a
//      bright node visibly bleeds a soft halo into its surrounding dark
//      texture instead of only brightening in isolation - approximating
//      what a real bloom pass does. An 8-tap in-shader blur (sampling 8
//      neighboring UVs per fragment, every frame) was tried first and
//      measured at 15-17fps in this environment, down from 33-43fps - the
//      redundant per-fragment texture fetches were themselves the cost,
//      independent of any render-to-texture pipeline. Pre-blurring once
//      drops this to 2 texture reads per fragment (same as before the
//      bloom attempt) with the expensive part paid a single time at
//      mount, not every frame.
const SURFACE_VERTEX_SHADER = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const SURFACE_FRAGMENT_SHADER = `
  uniform sampler2D map;
  uniform sampler2D blurMap;
  uniform float glowBoost;
  uniform float bloomStrength;
  varying vec2 vUv;

  void main() {
    vec3 texColor = texture2D(map, vUv).rgb;
    vec3 bloom = texture2D(blurMap, vUv).rgb;
    vec3 boosted = texColor * (1.0 + glowBoost) + bloom * bloomStrength;
    gl_FragColor = vec4(boosted, 1.0);
  }
`;

// Draws the loaded image at a small size onto a canvas, then displays it far
// larger - the GPU's own bilinear upscaling does the blurring, for free, at
// draw time. Classic cheap approximate-blur trick, no shader blur pass
// needed at all.
function makeBlurredTexture(image: HTMLImageElement, targetWidth = 96) {
  const canvas = document.createElement("canvas");
  canvas.width = targetWidth;
  canvas.height = Math.max(1, Math.round(targetWidth * (image.height / image.width)));
  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.magFilter = THREE.LinearFilter;
  tex.minFilter = THREE.LinearFilter;
  tex.generateMipmaps = false;
  return tex;
}

// Soft ambient edge bleed - the same Fresnel mechanism as before, but tuned
// in the opposite direction: a low power (wide, gradual falloff spanning a
// large fraction of the visible cap, not a thin band) and low intensity (so
// it reads as gentle light bleeding into the black background, not a bright
// defined line). Deliberately not the same shader as the ray-burst/hard-ring
// attempts - this is meant to feel like ambient glow, not an edge marking.
const EDGE_VERTEX_SHADER = `
  varying vec3 vNormal;
  varying vec3 vViewDir;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewDir = normalize(-mvPosition.xyz);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const EDGE_FRAGMENT_SHADER = `
  uniform vec3 glowColor;
  uniform float glowPower;
  uniform float glowIntensity;
  varying vec3 vNormal;
  varying vec3 vViewDir;
  void main() {
    float fresnel = 1.0 - max(dot(vViewDir, vNormal), 0.0);
    float rim = pow(fresnel, glowPower) * glowIntensity;
    gl_FragColor = vec4(glowColor * rim, rim);
  }
`;

interface HeroSphereProps {
  hovered: boolean;
  exploring: boolean;
  onPointerOver: () => void;
  onPointerOut: () => void;
  onClick: (event: ThreeEvent<MouseEvent>) => void;
}

export function HeroSphere({ hovered, exploring, onPointerOver, onPointerOut, onClick }: HeroSphereProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const edgeMaterialRef = useRef<THREE.ShaderMaterial>(null);
  const texture = useLoader(THREE.TextureLoader, "/images/hero-global-network.png");
  texture.colorSpace = THREE.SRGBColorSpace;
  // Mipmaps off: at the sphere's UV seam (u=0 meets u=1 - the source photo
  // isn't a seamless equirectangular map, so content doesn't match across
  // it), triangles on either side of that seam have near-opposite UV
  // derivatives. Mipmap LOD selection uses those derivatives, so it was
  // picking a wrong/low level right at the seam - a dark band that swept
  // through as a visible flash once per rotation. Plain bilinear sampling
  // has no LOD to get wrong, so the seam is still a seam (a thin content
  // discontinuity) but never a flash.
  texture.generateMipmaps = false;
  texture.minFilter = THREE.LinearFilter;

  const blurTexture = useMemo(() => makeBlurredTexture(texture.image as HTMLImageElement), [texture]);

  const surfaceUniforms = useMemo(
    () => ({
      map: { value: texture },
      blurMap: { value: blurTexture },
      glowBoost: { value: 0.55 },
      bloomStrength: { value: 2.2 },
    }),
    [texture, blurTexture],
  );

  const edgeUniforms = useMemo(
    () => ({
      glowColor: { value: GLOW_COLOR },
      glowPower: { value: 2.2 },
      glowIntensity: { value: 0.5 },
    }),
    [],
  );

  useFrame((_, delta) => {
    const mesh = meshRef.current;
    const group = groupRef.current;
    if (!mesh || !group) return;

    // delta-scaled so spin rate is identical regardless of frame rate
    mesh.rotation.y += delta * ROTATION_SPEED;

    // Exit translation (below) drives its own scale/position via GSAP once
    // exploring flips true, so the lerp-toward-1.1 here is only relevant
    // for the brief pre-exit hold and is harmless once GSAP takes over.
    const targetScale = exploring ? 1.1 : hovered ? 1.02 : 1;
    group.scale.setScalar(THREE.MathUtils.lerp(group.scale.x, targetScale, 0.1));

    if (edgeMaterialRef.current) {
      const targetIntensity = exploring ? 0.75 : hovered ? 0.62 : 0.5;
      edgeMaterialRef.current.uniforms.glowIntensity.value = THREE.MathUtils.lerp(
        edgeMaterialRef.current.uniforms.glowIntensity.value,
        targetIntensity,
        0.1,
      );
    }
  });

  // Exit animation: rotate further + translate fully off-screen right, on
  // a GSAP timeline (per the brief) rather than useFrame, since this is a
  // one-shot eased tween, not a continuous per-frame update.
  useEffect(() => {
    if (!exploring) return;
    const group = groupRef.current;
    const mesh = meshRef.current;
    if (!group || !mesh) return;

    const tl = gsap.timeline();
    tl.to(
      group.position,
      { x: EXIT_X, duration: EXIT_DURATION, ease: "power2.in" },
      0,
    ).to(
      mesh.rotation,
      { y: `+=${Math.PI * 0.6}`, duration: EXIT_DURATION, ease: "power1.in" },
      0,
    );

    return () => {
      tl.kill();
    };
  }, [exploring]);

  return (
    <group ref={groupRef} position={[0, GROUP_Y, 0]}>
      <mesh ref={meshRef} onPointerOver={onPointerOver} onPointerOut={onPointerOut} onClick={onClick}>
        <sphereGeometry args={[SPHERE_RADIUS, 64, 64]} />
        <shaderMaterial
          uniforms={surfaceUniforms}
          vertexShader={SURFACE_VERTEX_SHADER}
          fragmentShader={SURFACE_FRAGMENT_SHADER}
        />
      </mesh>
      {/*
        Soft ambient edge glow: additive-blended, depth-write off, raycast
        disabled so it never steals clicks meant for the main sphere. Lower
        segment count than the main sphere (32 vs 64) - a smooth gradient
        effect like this doesn't need the extra subdivision, and it measurably
        cut this mesh's own cost with no visible difference.
      */}
      <mesh scale={1.02} raycast={() => null}>
        <sphereGeometry args={[SPHERE_RADIUS, 32, 32]} />
        <shaderMaterial
          ref={edgeMaterialRef}
          uniforms={edgeUniforms}
          vertexShader={EDGE_VERTEX_SHADER}
          fragmentShader={EDGE_FRAGMENT_SHADER}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}
