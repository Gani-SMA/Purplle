import React, { useRef, useEffect, ReactNode } from 'react';

interface FrostedGlassCardProps {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  noTilt?: boolean;
  padding?: string | number;
  /** Accent glow color on hover — e.g. '#818cf8' or 'rgba(52,211,153,0.7)' */
  glowColor?: string;
}

/** Parse any CSS color string and return {r,g,b} 0-255, or null on failure */
function parseColorRGB(c: string): { r: number; g: number; b: number } | null {
  // Handle #rrggbb and #rgb
  const hex6 = c.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
  if (hex6) return { r: parseInt(hex6[1],16), g: parseInt(hex6[2],16), b: parseInt(hex6[3],16) };
  const hex3 = c.match(/^#([0-9a-f])([0-9a-f])([0-9a-f])$/i);
  if (hex3) return { r: parseInt(hex3[1]+hex3[1],16), g: parseInt(hex3[2]+hex3[2],16), b: parseInt(hex3[3]+hex3[3],16) };
  // Handle rgba(...) — take only rgb channels
  const rgba = c.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
  if (rgba) return { r: +rgba[1], g: +rgba[2], b: +rgba[3] };
  return null;
}

export const FrostedGlassCard: React.FC<FrostedGlassCardProps> = ({
  children,
  className = '',
  style,
  noTilt = false,
  padding,
  glowColor = '#818cf8',
}) => {
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;

    // Pre-parse glow color once → derive three alpha variants
    const rgb = parseColorRGB(glowColor) ?? { r: 129, g: 140, b: 248 };
    const glowTight  = `rgba(${rgb.r},${rgb.g},${rgb.b},0.65)`;
    const glowMid    = `rgba(${rgb.r},${rgb.g},${rgb.b},0.32)`;
    const glowOuter  = `rgba(${rgb.r},${rgb.g},${rgb.b},0.13)`;

    card.style.setProperty('--glow-color',  glowTight);
    card.style.setProperty('--glow-mid',    glowMid);
    card.style.setProperty('--glow-outer',  glowOuter);
    card.style.setProperty('--glow-sparkle',glowMid);

    let raf = 0;
    let lastX = 0, lastY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      lastX = e.clientX;
      lastY = e.clientY;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const rect = card.getBoundingClientRect();
        const x = lastX - rect.left;
        const y = lastY - rect.top;
        const cx = rect.width / 2;
        const cy = rect.height / 2;

        const rotY = noTilt ? 0 :  (x - cx) / cx * 14;
        const rotX = noTilt ? 0 : -(y - cy) / cy * 14;

        card.style.transform = noTilt
          ? 'scale(1.012) translateY(-3px)'
          : `perspective(800px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(1.025) translateZ(8px)`;

        card.style.setProperty('--mouse-x', `${x}px`);
        card.style.setProperty('--mouse-y', `${y}px`);
      });
    };

    const handleMouseEnter = () => {
      // Fast response on enter, spring-back on leave (set by leave handler)
      card.style.transition = 'border-color 0.15s, box-shadow 0.15s, filter 0.15s';
    };

    const handleMouseLeave = () => {
      cancelAnimationFrame(raf);
      card.style.transform = '';
      card.style.transition =
        'transform 0.60s cubic-bezier(0.22,1,0.36,1), border-color 0.3s, box-shadow 0.4s, filter 0.35s';
    };

    card.addEventListener('mousemove',  handleMouseMove);
    card.addEventListener('mouseenter', handleMouseEnter);
    card.addEventListener('mouseleave', handleMouseLeave);
    return () => {
      cancelAnimationFrame(raf);
      card.removeEventListener('mousemove',  handleMouseMove);
      card.removeEventListener('mouseenter', handleMouseEnter);
      card.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [noTilt, glowColor]);

  return (
    <div
      ref={cardRef}
      className={`fgc ${className}`}
      style={{
        padding: padding !== undefined ? padding : undefined,
        ...style,
      }}
    >
      <div className="fgc-glare"   aria-hidden="true" />
      <div className="fgc-sparkle" aria-hidden="true" />
      {children}
    </div>
  );
};
