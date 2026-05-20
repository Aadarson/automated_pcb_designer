import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';

interface ComponentPlacement {
  ref: string;
  x: float;
  y: float;
  w: float;
  h: float;
  layer: string;
}

interface PCB3DViewProps {
  width: number;
  height: number;
  placements: ComponentPlacement[];
}

const ComponentBox = ({ p, pcbWidth, pcbHeight }: { p: ComponentPlacement, pcbWidth: number, pcbHeight: number }) => {
  // Center is (0,0) in Three.js, so we shift by half-board
  const x = p.x - pcbWidth / 2;
  const z = p.y - pcbHeight / 2;
  const thickness = 1.5; // mm

  return (
    <mesh position={[x, thickness/2 + 0.1, z]}>
      <boxGeometry args={[p.w, thickness, p.h]} />
      <meshStandardMaterial color={p.ref.startsWith('U') ? '#3498db' : '#95a5a6'} roughness={0.3} metalness={0.2} />
    </mesh>
  );
};

const BoardSubstrate = ({ width, height }: { width: number, height: number }) => {
  return (
    <mesh position={[0, -0.8, 0]}>
      <boxGeometry args={[width, 1.6, height]} />
      <meshStandardMaterial color="#2c3e50" roughness={0.1} metalness={0.5} />
    </mesh>
  );
};

export const PCB3DView: React.FC<PCB3DViewProps> = ({ width, height, placements }) => {
  return (
    <div style={{ width: '100%', height: '500px', background: '#1a1a1a', borderRadius: '12px', overflow: 'hidden' }}>
      <Canvas shadows>
        <PerspectiveCamera makeDefault position={[width, 50, height]} />
        <OrbitControls makeDefault />
        <ambientLight intensity={0.5} />
        <spotLight position={[100, 100, 100]} angle={0.15} penumbra={1} intensity={1} castShadow />
        
        <BoardSubstrate width={width} height={height} />
        
        {placements.map((p) => (
          <ComponentBox key={p.ref} p={p} pcbWidth={width} pcbHeight={height} />
        ))}
        
        <ContactShadows opacity={0.4} scale={200} blur={24} far={10} />
        <Environment preset="city" />
      </Canvas>
    </div>
  );
};
