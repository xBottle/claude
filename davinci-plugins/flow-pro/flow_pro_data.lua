-- Автосгенерировано build_flow_pro.py — не редактировать руками.
return {
  PRESET_NAMES = { "Удар", "Мягкий флоу", "Разгон", "Рывок", "Замирание", "Бумеранг", "Толчок камеры", "Наезд", "Слайд вправо", "Слайд влево", "Вращение", "Кино", "Сон", "Жёсткий клип" },
  CURVES = { "Удар (быстро → медленно)", "Разгон (медленно → быстро)", "Плавно (S-кривая)", "Рывок в середине", "Замирание (удар и стоп)", "Бумеранг (туда-обратно)" },
  DEFAULTS = { GlobalMix = 1, ClipLen = 0, PerfOn = 0, RampOn = 1, RampType = 0, RampStrength = 0.6, RampAmount = 1, HoldPoint = 0.35, Quality = 1, TimeBlur = 0.5, MoveOn = 1, MoveType = 0, MoveStrength = 0.6, Zoom = 0.08, PanX = 0, PanY = 0, Rotate = 0, EdgeMode = 0, ShakeOn = 1, ShakeMode = 0, ShakeAmount = 0.8, ShakeDecay = 0.35, ShakeX = 1, ShakeY = 0.6, ShakeRot = 1.5, ShakeFreq = 2, ShakeSeed = 0, MotionBlur = 0.5, WhipOn = 0, WhipDir = 1, WhipIn = 1, WhipOut = 1, WhipAmount = 0.6, WhipFrames = 6, WhipBlur = 1, LookOn = 1, Exposure = 0, Contrast = 0.1, Sat = 1, Warmth = 0, Vignette = 0.25, GlowOn = 0, GlowThreshold = 0.5, GlowGain = 1, GlowSize = 12, FadeIn = 0, FadeOut = 0 },
  PRESETS = {
    [0] = {  },
    [1] = { RampType = 2, RampStrength = 0.4, MoveType = 2, Zoom = 0.05, ShakeAmount = 0.4, TimeBlur = 0.8 },
    [2] = { RampType = 1, RampStrength = 0.6, MoveType = 1, Zoom = 0.12, ShakeMode = 2, WhipOn = 1, WhipIn = 0, WhipOut = 1 },
    [3] = { RampType = 3, RampStrength = 0.75, ShakeAmount = 1.2, Zoom = 0.06 },
    [4] = { RampType = 4, HoldPoint = 0.3, RampStrength = 0.7, Zoom = 0.06, ShakeAmount = 1 },
    [5] = { RampType = 5, RampStrength = 0.5, MoveOn = 0, ShakeOn = 0 },
    [6] = { RampOn = 0, MoveOn = 0, ShakeAmount = 1.6, ShakeRot = 3, ShakeDecay = 0.3, MotionBlur = 0.8 },
    [7] = { RampOn = 0, Zoom = 0.18, MoveStrength = 0.8, ShakeOn = 0 },
    [8] = { RampOn = 0, MoveOn = 0, ShakeOn = 0, WhipOn = 1, WhipDir = 1, WhipAmount = 0.8 },
    [9] = { RampOn = 0, MoveOn = 0, ShakeOn = 0, WhipOn = 1, WhipDir = 0, WhipAmount = 0.8 },
    [10] = { Rotate = 6, Zoom = 0.1, MoveStrength = 0.7, ShakeAmount = 0.5, EdgeMode = 0 },
    [11] = { RampType = 2, RampStrength = 0.5, Zoom = 0.05, Contrast = 0.2, Sat = 0.9, Warmth = 0.15, Vignette = 0.45, GlowOn = 1, GlowThreshold = 0.55, GlowGain = 0.8, FadeOut = 6, ShakeAmount = 0.4 },
    [12] = { RampType = 2, RampStrength = 0.4, TimeBlur = 1.2, GlowOn = 1, GlowThreshold = 0.35, GlowGain = 1.2, Exposure = 0.1, Contrast = -0.05, Warmth = 0.2, ShakeOn = 0, Zoom = 0.04 },
    [13] = { RampStrength = 1, ShakeAmount = 2, ShakeRot = 3, Zoom = 0.2, MoveStrength = 0.9, WhipOn = 1, WhipIn = 0, WhipOut = 1, WhipDir = 1, Contrast = 0.3, Vignette = 0.4 },
  },
}
