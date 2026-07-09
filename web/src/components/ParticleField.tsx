import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

const PARTICLE_COUNT = 50;
const MAX_LINES = 40;
const CONVERGE_DURATION = 0.55; // seconds, matches the ~400-600ms brief
const LIME = new THREE.Color("#a3e635");

// A solid, sharp-edged core (so points read as crisp pinpoints, not soft
// blobs) with a tight glow halo only in the outer ring. The previous curve
// started softening from the very center (0.4 stop at only 0.55 alpha),
// which spread the falloff across nearly the whole dot instead of just its
// edge - same lesson as the sphere's rim light: concentrate brightness at
// the defining feature, then let it fall off, don't soften from the start.
function makeDotTexture() {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.28, "rgba(255,255,255,0.95)");
  gradient.addColorStop(0.55, "rgba(255,255,255,0.22)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(canvas);
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  phase: number;
  pulseSpeed: number;
  brightness: number;
}

interface ParticleFieldProps {
  hovered: boolean;
  convergeSignal: number;
  convergePoint: { nx: number; ny: number } | null;
}

function ParticleField({ hovered, convergeSignal, convergePoint }: ParticleFieldProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const linesRef = useRef<THREE.LineSegments>(null);
  const frameCount = useRef(0);
  const lastSignalRef = useRef(convergeSignal);
  const convergeStartRef = useRef<number | null>(null);
  const { viewport } = useThree();
  const texture = useMemo(() => makeDotTexture(), []);

  // Region: upper two-thirds of the frame, avoiding the busiest bottom
  // third of landmass detail - matches where the photo's own bright nodes
  // cluster, so the overlay reads as integrated rather than scattered.
  const particles = useMemo<Particle[]>(() => {
    const w = viewport.width;
    const h = viewport.height;
    return Array.from({ length: PARTICLE_COUNT }, () => {
      const angle = Math.random() * Math.PI * 2;
      const speed = w * (0.00035 + Math.random() * 0.00065);
      return {
        x: (Math.random() - 0.5) * w * 1.05,
        y: h * (Math.random() * 0.62 - 0.08),
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed * 0.5,
        phase: Math.random() * Math.PI * 2,
        pulseSpeed: 0.5 + Math.random() * 0.4,
        brightness: 0.55 + Math.random() * 0.45,
      };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const colors = new Float32Array(PARTICLE_COUNT * 3);
    particles.forEach((p, i) => {
      positions[i * 3] = p.x;
      positions[i * 3 + 1] = p.y;
      positions[i * 3 + 2] = 0;
      colors[i * 3] = LIME.r;
      colors[i * 3 + 1] = LIME.g;
      colors[i * 3 + 2] = LIME.b;
    });
    return { positions, colors };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const linePositions = useMemo(() => new Float32Array(MAX_LINES * 2 * 3), []);

  useFrame(({ clock }) => {
    const pointsObj = pointsRef.current;
    if (!pointsObj) return;
    const posAttr = pointsObj.geometry.attributes.position as THREE.BufferAttribute;
    const colorAttr = pointsObj.geometry.attributes.color as THREE.BufferAttribute;
    const t = clock.elapsedTime;
    const w = viewport.width;
    const h = viewport.height;
    const halfW = w * 0.55;
    const topY = h * 0.62;
    const bottomY = -h * 0.1;

    // A new click signal starts a fresh converge pulse - the ref comparison
    // (not a useEffect) is what lets this react to prop changes from
    // directly inside the frame loop.
    if (convergeSignal !== lastSignalRef.current) {
      lastSignalRef.current = convergeSignal;
      convergeStartRef.current = t;
    }
    const convergeElapsed = convergeStartRef.current === null ? Infinity : t - convergeStartRef.current;
    const convergeActive = convergeElapsed < CONVERGE_DURATION && convergePoint !== null;
    // Strength ramps in then fades back out over the window - a pull, not a snap.
    const convergeStrength = convergeActive
      ? Math.sin((convergeElapsed / CONVERGE_DURATION) * Math.PI) * 0.05
      : 0;
    const targetX = convergePoint ? convergePoint.nx * (w / 2) : 0;
    const targetY = convergePoint ? convergePoint.ny * (h / 2) : 0;

    const hoverBoost = hovered ? 1.12 : 1;

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;

      if (convergeActive) {
        p.x += (targetX - p.x) * convergeStrength;
        p.y += (targetY - p.y) * convergeStrength;
      }

      // Wrap at the region edges rather than letting particles fly off
      // and vanish - keeps the drift feeling continuous, never migrating
      // across the whole canvas.
      if (p.x > halfW) p.x = -halfW;
      if (p.x < -halfW) p.x = halfW;
      if (p.y > topY) p.y = bottomY;
      if (p.y < bottomY) p.y = topY;

      posAttr.setXYZ(i, p.x, p.y, 0);

      const pulse = 0.4 + 0.3 * Math.sin(t * p.pulseSpeed + p.phase);
      const b = pulse * p.brightness * hoverBoost;
      colorAttr.setXYZ(i, LIME.r * b, LIME.g * b, LIME.b * b);
    }
    posAttr.needsUpdate = true;
    colorAttr.needsUpdate = true;

    // Connections recomputed every 20 frames only, not every frame - a
    // one-time O(n^2) distance scan at n=50 is trivial, but there is no
    // reason to redo it 60x/sec when the lines only need to look like they
    // occasionally re-form.
    frameCount.current += 1;
    if (linesRef.current && frameCount.current % 20 === 0) {
      const threshold = w * 0.12;
      let count = 0;
      outer: for (let i = 0; i < PARTICLE_COUNT; i++) {
        for (let j = i + 1; j < PARTICLE_COUNT; j++) {
          if (count >= MAX_LINES) break outer;
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          if (Math.sqrt(dx * dx + dy * dy) < threshold) {
            linePositions[count * 6] = particles[i].x;
            linePositions[count * 6 + 1] = particles[i].y;
            linePositions[count * 6 + 2] = 0;
            linePositions[count * 6 + 3] = particles[j].x;
            linePositions[count * 6 + 4] = particles[j].y;
            linePositions[count * 6 + 5] = 0;
            count += 1;
          }
        }
      }
      const lineGeom = linesRef.current.geometry;
      lineGeom.setDrawRange(0, count * 2);
      (lineGeom.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    }

    if (linesRef.current) {
      const mat = linesRef.current.material as THREE.LineBasicMaterial;
      const baseOpacity = 0.12 + 0.08 * Math.sin(t * 0.25);
      mat.opacity = hovered ? baseOpacity * 1.15 : baseOpacity;
    }
  });

  return (
    <group>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
          <bufferAttribute attach="attributes-color" args={[colors, 3]} />
        </bufferGeometry>
        <pointsMaterial
          size={Math.max(viewport.width * 0.006, 4)}
          map={texture}
          transparent
          vertexColors
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          sizeAttenuation
        />
      </points>
      <lineSegments ref={linesRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linePositions, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color="#a3e635" transparent opacity={0.15} />
      </lineSegments>
    </group>
  );
}

interface ParticleOverlayProps {
  hovered?: boolean;
  convergeSignal?: number;
  convergePoint?: { nx: number; ny: number } | null;
}

// Public wrapper: owns the <Canvas>, transparent so the static hero image
// shows through beneath it, pointer-events disabled so it never blocks the
// globe button/scroll-indicator sitting above or around it.
export function ParticleOverlay({
  hovered = false,
  convergeSignal = 0,
  convergePoint = null,
}: ParticleOverlayProps) {
  return (
    <Canvas
      orthographic
      camera={{ position: [0, 0, 100], zoom: 1 }}
      gl={{ alpha: true, antialias: true }}
      dpr={[1, 2]}
      className="pointer-events-none"
    >
      <ParticleField hovered={hovered} convergeSignal={convergeSignal} convergePoint={convergePoint} />
    </Canvas>
  );
}
