import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'

class Vector2D {
  constructor(public x: number, public y: number) {}
  static random(min: number, max: number): number {
    return min + Math.random() * (max - min)
  }
}

class Vector3D {
  constructor(public x: number, public y: number, public z: number) {}
}

class AnimationController {
  private timeline: gsap.core.Timeline
  private time = 0
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D
  private size: number
  private stars: Star[] = []

  readonly changeEventTime = 0.32
  readonly cameraZ = -400
  readonly cameraTravelDistance = 3400
  private readonly startDotYOffset = 28
  readonly viewZoom = 100
  private readonly numberOfStars = 5000
  private readonly trailLength = 80

  constructor(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D, _dpr: number, size: number) {
    this.canvas = canvas
    this.ctx = ctx
    this.size = size
    this.timeline = gsap.timeline({ repeat: -1 })
    this.setupStars()
    this.setupTimeline()
  }

  private setupStars() {
    const orig = Math.random
    let seed = 1234
    Math.random = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280 }
    for (let i = 0; i < this.numberOfStars; i++) this.stars.push(new Star(this.cameraZ, this.cameraTravelDistance))
    Math.random = orig
  }

  private setupTimeline() {
    this.timeline.to(this, { time: 1, duration: 15, repeat: -1, ease: 'none', onUpdate: () => this.render() })
  }

  ease(p: number, g: number): number {
    return p < 0.5 ? 0.5 * Math.pow(2 * p, g) : 1 - 0.5 * Math.pow(2 * (1 - p), g)
  }

  easeOutElastic(x: number): number {
    const c4 = (2 * Math.PI) / 4.5
    if (x <= 0) return 0
    if (x >= 1) return 1
    return Math.pow(2, -8 * x) * Math.sin((x * 8 - 0.75) * c4) + 1
  }

  map(value: number, s1: number, e1: number, s2: number, e2: number): number {
    return s2 + (e2 - s2) * ((value - s1) / (e1 - s1))
  }

  constrain(v: number, min: number, max: number): number {
    return Math.min(Math.max(v, min), max)
  }

  lerp(a: number, b: number, t: number): number {
    return a * (1 - t) + b * t
  }

  spiralPath(p: number): Vector2D {
    p = this.constrain(1.2 * p, 0, 1)
    p = this.ease(p, 1.8)
    const turns = 6
    const theta = 2 * Math.PI * turns * Math.sqrt(p)
    const r = 170 * Math.sqrt(p)
    return new Vector2D(r * Math.cos(theta), r * Math.sin(theta) + this.startDotYOffset)
  }

  rotate(v1: Vector2D, v2: Vector2D, p: number, orientation: boolean): Vector2D {
    const mx = (v1.x + v2.x) / 2, my = (v1.y + v2.y) / 2
    const dx = v1.x - mx, dy = v1.y - my
    const angle = Math.atan2(dy, dx)
    const o = orientation ? -1 : 1
    const r = Math.sqrt(dx * dx + dy * dy)
    const bounce = Math.sin(p * Math.PI) * 0.05 * (1 - p)
    return new Vector2D(
      mx + r * (1 + bounce) * Math.cos(angle + o * Math.PI * this.easeOutElastic(p)),
      my + r * (1 + bounce) * Math.sin(angle + o * Math.PI * this.easeOutElastic(p))
    )
  }

  showProjectedDot(position: Vector3D, sizeFactor: number) {
    const t2 = this.constrain(this.map(this.time, this.changeEventTime, 1, 0, 1), 0, 1)
    const newCameraZ = this.cameraZ + this.ease(Math.pow(t2, 1.2), 1.8) * this.cameraTravelDistance
    if (position.z > newCameraZ) {
      const depth = position.z - newCameraZ
      const x = this.viewZoom * position.x / depth
      const y = this.viewZoom * position.y / depth
      const sw = 400 * sizeFactor / depth
      this.ctx.lineWidth = sw
      this.ctx.beginPath()
      this.ctx.arc(x, y, 0.5, 0, Math.PI * 2)
      this.ctx.fill()
    }
  }

  private drawStartDot() {
    if (this.time > this.changeEventTime) {
      const dy = this.cameraZ * this.startDotYOffset / this.viewZoom
      this.showProjectedDot(new Vector3D(0, dy, this.cameraTravelDistance), 2.5)
    }
  }

  render() {
    const ctx = this.ctx
    // Black background fill
    ctx.fillStyle = 'rgb(10,10,11)'
    ctx.fillRect(0, 0, this.size, this.size)

    ctx.save()
    ctx.translate(this.size / 2, this.size / 2)

    const t1 = this.constrain(this.map(this.time, 0, this.changeEventTime + 0.25, 0, 1), 0, 1)
    const t2 = this.constrain(this.map(this.time, this.changeEventTime, 1, 0, 1), 0, 1)

    ctx.rotate(-Math.PI * this.ease(t2, 2.7))
    this.drawTrail(t1)

    ctx.fillStyle = 'white'
    for (const star of this.stars) star.render(t1, this)

    this.drawStartDot()
    ctx.restore()
  }

  private drawTrail(t1: number) {
    for (let i = 0; i < this.trailLength; i++) {
      const f = this.map(i, 0, this.trailLength, 1.1, 0.1)
      const sw = (1.3 * (1 - t1) + 3.0 * Math.sin(Math.PI * t1)) * f
      this.ctx.fillStyle = 'white'
      this.ctx.lineWidth = sw
      const pos = this.spiralPath(t1 - 0.00015 * i)
      const offset = new Vector2D(pos.x + 5, pos.y + 5)
      const rotated = this.rotate(pos, offset, Math.sin(this.time * Math.PI * 2) * 0.5 + 0.5, i % 2 === 0)
      this.ctx.beginPath()
      this.ctx.arc(rotated.x, rotated.y, sw / 2, 0, Math.PI * 2)
      this.ctx.fill()
    }
  }

  pause()   { this.timeline.pause() }
  resume()  { this.timeline.play() }
  destroy() { this.timeline.kill() }
}

class Star {
  private dx: number
  private dy: number
  private spiralLocation: number
  private strokeWeightFactor: number
  private z: number
  private angle: number
  private distance: number
  private rotationDirection: number
  private expansionRate: number
  private finalScale: number

  constructor(cameraZ: number, cameraTravelDistance: number) {
    this.angle = Math.random() * Math.PI * 2
    this.distance = 30 * Math.random() + 15
    this.rotationDirection = Math.random() > 0.5 ? 1 : -1
    this.expansionRate = 1.2 + Math.random() * 0.8
    this.finalScale = 0.7 + Math.random() * 0.6
    this.dx = this.distance * Math.cos(this.angle)
    this.dy = this.distance * Math.sin(this.angle)
    this.spiralLocation = (1 - Math.pow(1 - Math.random(), 3.0)) / 1.3
    this.z = Vector2D.random(0.5 * cameraZ, cameraTravelDistance + cameraZ)
    const lerp = (a: number, b: number, t: number) => a * (1 - t) + b * t
    this.z = lerp(this.z, cameraTravelDistance / 2, 0.3 * this.spiralLocation)
    this.strokeWeightFactor = Math.pow(Math.random(), 2.0)
  }

  render(p: number, c: AnimationController) {
    const spiralPos = c.spiralPath(this.spiralLocation)
    const q = p - this.spiralLocation
    if (q <= 0) return

    const dp = c.constrain(4 * q, 0, 1)
    const linear = dp, elastic = c.easeOutElastic(dp), power = Math.pow(dp, 2)

    let easing: number
    if (dp < 0.3)      easing = c.lerp(linear, power, dp / 0.3)
    else if (dp < 0.7) easing = c.lerp(power, elastic, (dp - 0.3) / 0.4)  // eslint-disable-line @typescript-eslint/no-unused-vars
    else               easing = elastic

    let sx: number, sy: number

    if (dp < 0.3) {
      sx = c.lerp(spiralPos.x, spiralPos.x + this.dx * 0.3, easing / 0.3)
      sy = c.lerp(spiralPos.y, spiralPos.y + this.dy * 0.3, easing / 0.3)
    } else if (dp < 0.7) {
      const mp = (dp - 0.3) / 0.4
      const curve = Math.sin(mp * Math.PI) * this.rotationDirection * 1.5
      const bx = spiralPos.x + this.dx * 0.3, by = spiralPos.y + this.dy * 0.3
      const tx = spiralPos.x + this.dx * 0.7, ty = spiralPos.y + this.dy * 0.7
      sx = c.lerp(bx, tx, mp) + (-this.dy * 0.4 * curve) * mp
      sy = c.lerp(by, ty, mp) + (this.dx * 0.4 * curve) * mp
    } else {
      const fp = (dp - 0.7) / 0.3
      const bx = spiralPos.x + this.dx * 0.7, by = spiralPos.y + this.dy * 0.7
      const td = this.distance * this.expansionRate * 1.5
      const sa = this.angle + 1.2 * this.rotationDirection * fp * Math.PI
      sx = c.lerp(bx, spiralPos.x + td * Math.cos(sa), fp)
      sy = c.lerp(by, spiralPos.y + td * Math.sin(sa), fp)
    }

    const vx = (this.z - (c as any).cameraZ) * sx / (c as any).viewZoom
    const vy = (this.z - (c as any).cameraZ) * sy / (c as any).viewZoom

    let size = 1.0
    if (dp < 0.6) size = 1.0 + dp * 0.2
    else { const t = (dp - 0.6) / 0.4; size = 1.2 * (1 - t) + this.finalScale * t }

    c.showProjectedDot(new Vector3D(vx, vy, this.z), 8.5 * this.strokeWeightFactor * size)
  }
}

export function SpiralAnimation() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<AnimationController | null>(null)
  const [dims, setDims] = useState({ w: window.innerWidth, h: window.innerHeight })

  useEffect(() => {
    const handle = () => setDims({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', handle)
    return () => window.removeEventListener('resize', handle)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const size = Math.max(dims.w, dims.h)
    canvas.width = size * dpr
    canvas.height = size * dpr
    canvas.style.width  = `${dims.w}px`
    canvas.style.height = `${dims.h}px`
    ctx.scale(dpr, dpr)

    animRef.current = new AnimationController(canvas, ctx, dpr, size)
    return () => { animRef.current?.destroy(); animRef.current = null }
  }, [dims])

  return (
    <div style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
      <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
    </div>
  )
}
