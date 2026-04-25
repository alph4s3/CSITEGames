// ============================================================
//  FIBONACCI ADVENTURE – Grow Your Own Magic Spiral
//  A p5.js educational game for high school students
// ============================================================
//
//  HOW TO RUN:
//  1. Go to https://editor.p5js.org/
//  2. Delete all existing code in the editor
//  3. Paste this entire file into the editor
//  4. Click the ▶ Play button — enjoy!
//
//  WHAT YOU'LL LEARN:
//  - What the Fibonacci sequence is (1,1,2,3,5,8,13,21...)
//  - How it creates the golden spiral found in nature
//  - Basic coding concepts: variables, arrays, functions, loops
// ============================================================

// ---- GAME STATE ----
// We use a simple string to track which "screen" we're on.
// Possible values: "start", "play", "end"
let gameState = "start";

// ---- FIBONACCI DATA ----
let fibSequence = [];        // Stores numbers player has added so far
let maxFibNumbers = 12;      // Game ends when this many numbers are added
let animProgress = 0;        // 0→1 float that controls spiral growth animation
let animating = false;       // Are we currently animating a new number?
let totalAngle = 0;          // How much of the spiral is drawn (in radians)
let targetAngle = 0;         // What totalAngle is animating toward

// ---- THEMES ----
// Each theme has: a name, background colors, spiral color, particle colors
let themes = [
  {
    name: "🌸 Flower Garden",
    bgTop:    [20,  10,  40],   // Dark purple-ish sky
    bgBot:    [10,  40,  10],   // Dark green ground
    spiralColor: [255, 215, 0], // Gold
    particles: [
      [255, 100, 180], [255, 200, 80],
      [180, 100, 255], [100, 255, 150]
    ]
  },
  {
    name: "🐚 Ocean Shells",
    bgTop:    [0,   20,  60],   // Deep ocean blue
    bgBot:    [0,   60,  80],   // Teal water
    spiralColor: [0, 220, 255], // Cyan
    particles: [
      [0, 180, 255], [0, 255, 200],
      [100, 200, 255], [200, 240, 255]
    ]
  },
  {
    name: "🌌 Space Galaxy",
    bgTop:    [5,   0,   20],   // Deep space
    bgBot:    [20,  0,   50],   // Dark violet
    spiralColor: [200, 100, 255], // Purple
    particles: [
      [255, 255, 100], [200, 100, 255],
      [100, 200, 255], [255, 150, 50]
    ]
  }
];
let currentTheme = 0; // Index into the themes array

// ---- PARTICLES ----
// Each particle is an object with position, velocity, life, color, etc.
let particles = [];

// ---- FLOATING NUMBERS ----
// Decorative Fibonacci numbers that drift around the screen
let floaters = [];

// ---- CONFETTI (end screen) ----
let confetti = [];

// ---- BUTTONS ----
// We store button info as objects; drawing & clicking are handled manually
// This keeps the code simple without needing p5.js DOM library
let startBtn, addBtn, themeButtons = [];

// ---- ROBOT messages ----
// The little robot guide cycles through these encouraging messages
let robotMessages = [
  "Hi! I'm Phi-Bot! 🤖",
  "Click ADD to start!",
  "1 + 1 = 2. Easy!",
  "Each number = the sum of the last two!",
  "This is the Fibonacci sequence!",
  "Found in flowers, shells & galaxies!",
  "You're doing amazing! 🌟",
  "Keep going! Watch the spiral grow!",
  "Nature uses this pattern everywhere!",
  "You're almost a Fibonacci master!",
  "φ = 1.618... the golden ratio! ✨",
  "Incredible! Nature's blueprint! 🌀"
];
let robotFrame = 0;   // Tracks which message to show
let robotBlink = 0;   // Controls eye blinking animation

// ---- p5.js SETUP ----
// Called once when the sketch starts. We set up canvas and initialize objects.
function setup() {
  createCanvas(600, 700);
  textFont("monospace");

  // Build button objects (x, y, width, height, label, color)
  startBtn = makeButton(200, 420, 200, 55, "▶  START", [80, 220, 120]);

  addBtn = makeButton(210, 590, 180, 48, "+ ADD NEXT", [255, 200, 0]);

  // Theme buttons - one per theme, arranged in a row
  for (let i = 0; i < themes.length; i++) {
    themeButtons.push(
      makeButton(20 + i * 190, 10, 175, 35, themes[i].name, [80, 80, 160])
    );
  }

  // Seed the background with some floating decorative numbers
  for (let i = 0; i < 10; i++) {
    floaters.push(makeFloater());
  }

  // Start with the first two Fibonacci numbers already placed
  // (So the player sees context immediately when they start)
  // These get added when play starts — see startGame()
}

// ============================================================
//  p5.js DRAW — called 60 times per second
//  This is the main "game loop"
// ============================================================
function draw() {
  // Route to the correct screen based on gameState
  if (gameState === "start") {
    drawStartScreen();
  } else if (gameState === "play") {
    drawPlayScreen();
  } else if (gameState === "end") {
    drawEndScreen();
  }

  // Floating numbers appear on ALL screens for visual flair
  updateAndDrawFloaters();
}

// ============================================================
//  START SCREEN
// ============================================================
function drawStartScreen() {
  // Draw gradient background
  drawBackground();

  // Decorative golden spiral behind the title (static preview)
  push();
  translate(width / 2, height / 2 + 40);
  drawSpiral(PI * 5, [255, 215, 0], 0.7); // pre-drawn spiral, 70% opacity
  pop();

  // Title text with glow effect
  drawGlowText("FIBONACCI", width / 2, 140, 54, [255, 215, 0], 20);
  drawGlowText("ADVENTURE", width / 2, 200, 54, [255, 215, 0], 20);

  fill(200, 240, 255);
  textSize(20);
  textAlign(CENTER, CENTER);
  text("Grow Your Own Magic Spiral 🌀", width / 2, 250);

  // φ symbol rotating slowly
  push();
  translate(width / 2, 330);
  rotate(frameCount * 0.01);
  fill(255, 215, 0, 180);
  textSize(60);
  text("φ", 0, 0);
  pop();

  // Draw start button
  drawButton(startBtn);

  // Small instructions
  fill(180, 200, 255, 180);
  textSize(13);
  text("Discover the pattern hidden in nature!", width / 2, 500);
  text("No coding experience needed 🌱", width / 2, 520);

  // Draw the robot guide in the corner
  drawRobot(500, 540, "Hi! Click START! 🤖");
}

// ============================================================
//  PLAY SCREEN — the main game
// ============================================================
function drawPlayScreen() {
  drawBackground();

  // ---- Update animation ----
  if (animating) {
    // animProgress smoothly goes from 0 to 1
    animProgress += 0.035;
    totalAngle = lerp(totalAngle, targetAngle, 0.07);
    if (animProgress >= 1) {
      animProgress = 1;
      animating = false;
      robotFrame = min(robotFrame + 1, robotMessages.length - 1);
    }
  }

  // ---- Draw the spiral ----
  push();
  translate(width / 2, height / 2 - 20);
  let sc = themes[currentTheme].spiralColor;
  drawSpiral(totalAngle, sc, 1.0);
  pop();

  // ---- Draw particles ----
  updateAndDrawParticles();

  // ---- Theme selector buttons at top ----
  for (let i = 0; i < themeButtons.length; i++) {
    // Highlight the active theme
    themeButtons[i].highlighted = (i === currentTheme);
    drawButton(themeButtons[i]);
  }

  // ---- Fibonacci sequence display ----
  drawSequenceDisplay();

  // ---- Add button ----
  if (!animating) {
    drawButton(addBtn);
  } else {
    // Show "growing..." while animating
    fill(255, 215, 0, 180);
    textSize(16);
    textAlign(CENTER, CENTER);
    text("🌀 Growing...", 300, 614);
  }

  // ---- Golden ratio label ----
  if (fibSequence.length >= 3) {
    let last = fibSequence[fibSequence.length - 1];
    let prev = fibSequence[fibSequence.length - 2];
    let ratio = (last / prev).toFixed(4);
    fill(255, 215, 0, 200);
    textSize(14);
    textAlign(CENTER);
    text("φ ratio: " + last + "/" + prev + " ≈ " + ratio, width / 2, 558);
  }

  // ---- Robot guide ----
  drawRobot(480, 560, robotMessages[robotFrame]);

  // ---- Check win condition ----
  if (fibSequence.length >= maxFibNumbers && !animating) {
    gameState = "end";
    spawnConfetti();
  }
}

// ============================================================
//  END SCREEN — celebration!
// ============================================================
function drawEndScreen() {
  drawBackground();

  // Animate confetti
  updateAndDrawConfetti();

  // Big spiral (fully grown)
  push();
  translate(width / 2, height / 2 - 60);
  let sc = themes[currentTheme].spiralColor;
  drawSpiral(totalAngle, sc, 1.0);
  pop();

  // Pulsing celebration text
  let pulse = sin(frameCount * 0.08) * 8;
  drawGlowText("YOU GREW", width / 2, 130, 36 + pulse * 0.3, [255, 215, 0], 15);
  drawGlowText("NATURE'S BLUEPRINT!", width / 2, 175, 30 + pulse * 0.2, [255, 215, 0], 12);

  // φ symbol
  fill(255, 215, 0, 200);
  textSize(28 + sin(frameCount * 0.1) * 4);
  textAlign(CENTER, CENTER);
  text("φ = 1.618033...", width / 2, 220);

  // Call-to-action banners
  drawBanner(
    "🎓 ENROLL IN CSITE NOW!",
    width / 2, 490, [80, 40, 160], [255, 215, 0]
  );
  drawBanner(
    "LEARN HOW TO CODE 💻",
    width / 2, 538, [30, 100, 180], [255, 255, 255]
  );
  drawBanner(
    "BUILDING THE FUTURE WITH FIBONACCI! 🚀",
    width / 2, 586, [20, 120, 60], [255, 255, 200]
  );

  // Sequence recap
  fill(200, 240, 255, 210);
  textSize(13);
  textAlign(CENTER);
  text("Your sequence: " + fibSequence.join(", "), width / 2, 640);

  // Play again
  let replayBtn = makeButton(200, 655, 200, 42, "🔄 Play Again", [120, 60, 200]);
  drawButton(replayBtn);

  // Check if replay clicked (simple check)
  if (mouseIsPressed &&
      mouseX > replayBtn.x && mouseX < replayBtn.x + replayBtn.w &&
      mouseY > replayBtn.y && mouseY < replayBtn.y + replayBtn.h) {
    resetGame();
  }

  // Robot cheering
  drawRobot(490, 450, "AMAZING! 🎉\nYou did it!");
}

// ============================================================
//  DRAW THE FIBONACCI / GOLDEN SPIRAL
//  The spiral is drawn as a series of quarter-circle arcs,
//  each sized by the Fibonacci numbers.
//  angleLimit: how many radians of spiral to draw (controls growth)
//  col: [r, g, b] color array
//  alpha: 0-1 opacity
// ============================================================
function drawSpiral(angleLimit, col, alpha) {
  // Scale factor — keeps the spiral fitting nicely on screen
  let scale = 3.5;

  // We'll trace the spiral using Fibonacci arc sizes
  // Each quarter turn uses a square whose side = the next Fibonacci number
  let fibs = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233];

  // Starting position and angle for the spiral's center
  let cx = 0, cy = 0;
  let startAngle = PI;

  // Glow effect — draw a blurred version behind
  for (let glow = 3; glow >= 0; glow--) {
    noFill();
    stroke(col[0], col[1], col[2], (alpha * 60) / (glow + 1));
    strokeWeight(2 + glow * 3);

    let drawnAngle = 0;
    let px = cx, py = cy;
    let a = startAngle;

    for (let i = 0; i < fibs.length && drawnAngle < angleLimit; i++) {
      let r = fibs[i] * scale;
      let remaining = angleLimit - drawnAngle;
      let arcAngle = min(HALF_PI, remaining);

      arc(px, py, r * 2, r * 2, a, a + arcAngle);

      // Move center for next arc
      // Each arc rotates the pivot point
      let nextA = a + HALF_PI;
      let dx = cos(nextA + PI) * r;
      let dy = sin(nextA + PI) * r;
      // Pivot positions follow the Fibonacci tiling pattern
      if      (i % 4 === 0) { px += fibs[i] * scale; }
      else if (i % 4 === 1) { py += fibs[i] * scale; }
      else if (i % 4 === 2) { px -= fibs[i] * scale; }
      else if (i % 4 === 3) { py -= fibs[i] * scale; }

      drawnAngle += HALF_PI;
      a += HALF_PI;
    }
  }

  // Main bright spiral line on top
  noFill();
  stroke(col[0], col[1], col[2], alpha * 255);
  strokeWeight(2.5);

  let drawnAngle = 0;
  let px = cx, py = cy;
  let a = startAngle;

  for (let i = 0; i < fibs.length && drawnAngle < angleLimit; i++) {
    let r = fibs[i] * scale;
    let remaining = angleLimit - drawnAngle;
    let arcAngle = min(HALF_PI, remaining);

    arc(px, py, r * 2, r * 2, a, a + arcAngle);

    if      (i % 4 === 0) { px += fibs[i] * scale; }
    else if (i % 4 === 1) { py += fibs[i] * scale; }
    else if (i % 4 === 2) { px -= fibs[i] * scale; }
    else if (i % 4 === 3) { py -= fibs[i] * scale; }

    drawnAngle += HALF_PI;
    a += HALF_PI;
  }

  // Golden center dot
  noStroke();
  fill(col[0], col[1], col[2], alpha * 255);
  circle(cx, cy, 8);
  fill(255, 255, 255, alpha * 200);
  circle(cx, cy, 4);
}

// ============================================================
//  DRAW BACKGROUND — gradient sky-to-ground for current theme
// ============================================================
function drawBackground() {
  let t = themes[currentTheme];
  for (let y = 0; y < height; y++) {
    let amt = y / height;
    let r = lerp(t.bgTop[0], t.bgBot[0], amt);
    let g = lerp(t.bgTop[1], t.bgBot[1], amt);
    let b = lerp(t.bgTop[2], t.bgBot[2], amt);
    stroke(r, g, b);
    line(0, y, width, y);
  }

  // Subtle star-like dots for all themes
  randomSeed(42); // Fixed seed so stars don't flicker
  for (let i = 0; i < 60; i++) {
    let sx = random(width);
    let sy = random(height * 0.7);
    let bright = random(100, 200);
    let sz = random(1, 3);
    fill(bright, bright, bright, random(80, 180));
    noStroke();
    circle(sx, sy, sz);
  }
}

// ============================================================
//  DRAW THE FIBONACCI SEQUENCE DISPLAY (row of number chips)
// ============================================================
function drawSequenceDisplay() {
  let chipW = 42, chipH = 32;
  let startX = 20;
  let y = 660;

  // Label
  fill(200, 220, 255, 200);
  textSize(12);
  textAlign(LEFT, CENTER);
  text("Sequence:", startX, y - 18);

  for (let i = 0; i < fibSequence.length; i++) {
    let x = startX + i * (chipW + 4);

    // Last chip pulses / glows if we just added it
    if (i === fibSequence.length - 1) {
      fill(255, 215, 0, 60 + sin(frameCount * 0.2) * 40);
      noStroke();
      rect(x - 3, y - chipH / 2 - 3, chipW + 6, chipH + 6, 8);
    }

    // Chip background
    fill(60, 40, 100, 200);
    stroke(255, 215, 0, 160);
    strokeWeight(1);
    rect(x, y - chipH / 2, chipW, chipH, 6);

    // Number label
    fill(255, 215, 0);
    noStroke();
    textSize(fibSequence[i] > 99 ? 10 : 13);
    textAlign(CENTER, CENTER);
    text(fibSequence[i], x + chipW / 2, y);
  }

  // Show remaining slots as faint outlines
  for (let i = fibSequence.length; i < maxFibNumbers; i++) {
    let x = startX + i * (chipW + 4);
    noFill();
    stroke(100, 100, 150, 80);
    strokeWeight(1);
    rect(x, y - chipH / 2, chipW, chipH, 6);
  }
}

// ============================================================
//  ROBOT GUIDE — draws a cute pixel-art-style robot with a speech bubble
// ============================================================
function drawRobot(x, y, message) {
  push();
  translate(x, y);

  robotBlink++;
  let eyeH = (robotBlink % 80 < 5) ? 2 : 8; // Blink every ~80 frames

  // Body
  fill(30, 60, 140);
  stroke(100, 160, 255);
  strokeWeight(1.5);
  rect(-18, 20, 36, 40, 6);

  // Chest light
  fill(0, 220, 255, 150 + sin(frameCount * 0.1) * 80);
  circle(0, 40, 14);
  fill(255, 255, 255, 200);
  circle(0, 40, 7);

  // Head
  fill(20, 40, 100);
  stroke(100, 160, 255);
  rect(-16, -2, 32, 24, 8);

  // Eyes
  fill(0, 220, 255);
  noStroke();
  rect(-10, 4, 8, eyeH, 2);
  rect(2, 4, 8, eyeH, 2);

  // Antenna
  stroke(150, 200, 255);
  strokeWeight(2);
  line(0, -2, 0, -14);
  fill(255, 215, 0);
  noStroke();
  circle(0, -16, 7);

  // Arms
  fill(30, 60, 140);
  stroke(100, 160, 255);
  strokeWeight(1.5);
  rect(-28, 22, 10, 24, 5);
  rect(18, 22, 10, 24, 5);

  // Legs
  rect(-14, 60, 10, 18, 5);
  rect(4, 60, 10, 18, 5);

  // Speech bubble (only if message is not empty)
  if (message && message.length > 0) {
    let bw = max(message.length * 7, 80);
    let bx = -bw / 2 - 35;
    let by = -50;

    fill(255, 255, 255, 220);
    stroke(200, 200, 255, 200);
    strokeWeight(1);
    rect(bx, by, bw, 36, 8);

    // Bubble tail
    fill(255, 255, 255, 220);
    noStroke();
    triangle(bx + bw - 10, by + 36, bx + bw, by + 44, bx + bw + 4, by + 36);

    fill(40, 40, 80);
    noStroke();
    textSize(11);
    textAlign(CENTER, CENTER);
    text(message, bx + bw / 2, by + 18);
  }

  pop();
}

// ============================================================
//  PARTICLES — sparkle effects that burst when spiral grows
// ============================================================
function spawnParticles(n) {
  let colors = themes[currentTheme].particles;
  for (let i = 0; i < n; i++) {
    let c = random(colors);
    particles.push({
      x: width / 2 + random(-80, 80),
      y: height / 2 + random(-80, 80),
      vx: random(-4, 4),
      vy: random(-5, -1),
      life: 1.0,                  // 1.0 = fully alive, fades to 0
      decay: random(0.01, 0.025), // How fast it fades
      r: c[0], g: c[1], b: c[2],
      size: random(4, 12),
      shape: floor(random(3))     // 0=circle, 1=petal, 2=star
    });
  }
}

function updateAndDrawParticles() {
  for (let i = particles.length - 1; i >= 0; i--) {
    let p = particles[i];
    p.x += p.vx;
    p.y += p.vy;
    p.vy += 0.08; // Gravity
    p.life -= p.decay;

    if (p.life <= 0) {
      particles.splice(i, 1); // Remove dead particles
      continue;
    }

    let alpha = p.life * 255;
    fill(p.r, p.g, p.b, alpha);
    noStroke();

    if (p.shape === 0) {
      // Circle sparkle
      circle(p.x, p.y, p.size * p.life);
    } else if (p.shape === 1) {
      // Petal (ellipse)
      push();
      translate(p.x, p.y);
      rotate(p.vx);
      ellipse(0, 0, p.size * p.life, p.size * p.life * 0.5);
      pop();
    } else {
      // Star shape (4-pointed)
      push();
      translate(p.x, p.y);
      rotate(frameCount * 0.05);
      let s = p.size * p.life * 0.5;
      beginShape();
      for (let a = 0; a < TWO_PI; a += HALF_PI) {
        vertex(cos(a) * s, sin(a) * s);
        vertex(cos(a + QUARTER_PI) * s * 0.3, sin(a + QUARTER_PI) * s * 0.3);
      }
      endShape(CLOSE);
      pop();
    }
  }
}

// ============================================================
//  CONFETTI — celebration particles for end screen
// ============================================================
function spawnConfetti() {
  let cols = [
    [255, 80, 80], [80, 255, 80], [80, 80, 255],
    [255, 215, 0], [255, 80, 255], [80, 255, 255]
  ];
  for (let i = 0; i < 120; i++) {
    let c = random(cols);
    confetti.push({
      x: random(width),
      y: random(-100, 0),
      vx: random(-2, 2),
      vy: random(2, 6),
      r: c[0], g: c[1], b: c[2],
      size: random(6, 14),
      rot: random(TWO_PI),
      rotV: random(-0.1, 0.1)
    });
  }
}

function updateAndDrawConfetti() {
  for (let c of confetti) {
    c.x += c.vx;
    c.y += c.vy;
    c.rot += c.rotV;
    if (c.y > height + 20) {
      c.y = -20;
      c.x = random(width);
    }

    push();
    translate(c.x, c.y);
    rotate(c.rot);
    fill(c.r, c.g, c.b, 220);
    noStroke();
    rect(-c.size / 2, -c.size / 4, c.size, c.size / 2, 2);
    pop();
  }
}

// ============================================================
//  FLOATING BACKGROUND NUMBERS — decorative drifting Fibonacci numbers
// ============================================================
function makeFloater() {
  let fibNums = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144];
  return {
    x: random(width),
    y: random(height),
    n: random(fibNums),      // Which Fibonacci number to show
    vy: random(-0.4, -0.8),  // Drift upward slowly
    vx: random(-0.2, 0.2),
    alpha: random(30, 90),
    size: random(14, 28)
  };
}

function updateAndDrawFloaters() {
  let fibNums = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144];
  for (let f of floaters) {
    f.y += f.vy;
    f.x += f.vx;

    // Wrap around screen edges
    if (f.y < -30) { f.y = height + 10; f.x = random(width); }
    if (f.x < -30) { f.x = width + 10; }
    if (f.x > width + 30) { f.x = -10; }

    fill(255, 215, 0, f.alpha);
    noStroke();
    textSize(f.size);
    textAlign(CENTER, CENTER);
    textFont("monospace");
    text(f.n, f.x, f.y);
  }
}

// ============================================================
//  BUTTONS — simple rectangular buttons drawn with p5.js
// ============================================================
function makeButton(x, y, w, h, label, col) {
  return { x, y, w, h, label, col, highlighted: false };
}

function drawButton(btn) {
  let hover = (mouseX > btn.x && mouseX < btn.x + btn.w &&
               mouseY > btn.y && mouseY < btn.y + btn.h);

  // Shadow
  fill(0, 0, 0, 80);
  noStroke();
  rect(btn.x + 3, btn.y + 4, btn.w, btn.h, 10);

  // Button body — brighter when hovered or highlighted
  let brightness = (hover || btn.highlighted) ? 1.3 : 1.0;
  fill(
    min(btn.col[0] * brightness, 255),
    min(btn.col[1] * brightness, 255),
    min(btn.col[2] * brightness, 255)
  );
  stroke(255, 255, 255, 100);
  strokeWeight(1.5);
  rect(btn.x, btn.y, btn.w, btn.h, 10);

  // Label
  fill(255);
  noStroke();
  textSize(14);
  textAlign(CENTER, CENTER);
  text(btn.label, btn.x + btn.w / 2, btn.y + btn.h / 2);

  // Hover cursor hint
  if (hover) cursor(HAND);
}

// ============================================================
//  GLOW TEXT — draws text with a soft blurred glow behind it
// ============================================================
function drawGlowText(txt, x, y, sz, col, glowSize) {
  textAlign(CENTER, CENTER);
  // Outer glow passes
  for (let g = glowSize; g > 0; g -= 4) {
    fill(col[0], col[1], col[2], 30);
    textSize(sz + g);
    text(txt, x, y);
  }
  // Crisp main text
  fill(col[0], col[1], col[2]);
  textSize(sz);
  text(txt, x, y);
}

// ============================================================
//  DRAW BANNER — colored pill-shaped CTA banner
// ============================================================
function drawBanner(txt, x, y, bgCol, textCol) {
  let w = 540, h = 36;
  fill(bgCol[0], bgCol[1], bgCol[2], 220);
  stroke(255, 255, 255, 80);
  strokeWeight(1);
  rect(x - w / 2, y - h / 2, w, h, h / 2);
  fill(textCol[0], textCol[1], textCol[2]);
  noStroke();
  textSize(14);
  textAlign(CENTER, CENTER);
  text(txt, x, y);
}

// ============================================================
//  GAME LOGIC
// ============================================================

// Called when the Start button is clicked
function startGame() {
  gameState = "play";
  fibSequence = [1, 1];                  // Seed with first two numbers
  totalAngle = HALF_PI;                  // Start with a tiny spiral
  targetAngle = HALF_PI;
  animating = false;
  animProgress = 0;
  robotFrame = 2;
  particles = [];
}

// Add the next Fibonacci number to the sequence
function addNextFib() {
  if (animating) return; // Don't allow adding while animating
  if (fibSequence.length >= maxFibNumbers) return;

  // The next Fibonacci number = sum of the last two
  let len = fibSequence.length;
  let next = fibSequence[len - 1] + fibSequence[len - 2];
  fibSequence.push(next);

  // Each new number adds HALF_PI (90°) more to the spiral
  targetAngle += HALF_PI;

  // Start animating
  animating = true;
  animProgress = 0;

  // Burst of particles!
  spawnParticles(30);
}

// Reset everything for a new game
function resetGame() {
  gameState = "start";
  fibSequence = [];
  particles = [];
  confetti = [];
  totalAngle = 0;
  targetAngle = 0;
  animating = false;
  animProgress = 0;
  robotFrame = 0;
  cursor(ARROW);
}

// ============================================================
//  p5.js INPUT — mousePressed fires once per click
// ============================================================
function mousePressed() {
  cursor(ARROW); // Reset cursor

  // ---- Start screen ----
  if (gameState === "start") {
    if (isOver(startBtn)) startGame();
  }

  // ---- Play screen ----
  if (gameState === "play") {
    // Check theme buttons
    for (let i = 0; i < themeButtons.length; i++) {
      if (isOver(themeButtons[i])) {
        currentTheme = i;
        return;
      }
    }
    // Check add button
    if (isOver(addBtn) && !animating) {
      addNextFib();
    }
  }
}

// Helper: is the mouse over a button?
function isOver(btn) {
  return (mouseX > btn.x && mouseX < btn.x + btn.w &&
          mouseY > btn.y && mouseY < btn.y + btn.h);
}

// ============================================================
//  KEYBOARD SHORTCUT
//  Press SPACE to add the next number — handy alternative to clicking
// ============================================================
function keyPressed() {
  if (gameState === "play" && key === " ") {
    addNextFib();
  }
  if (gameState === "end" && key === " ") {
    resetGame();
  }
}

// ============================================================
//  EXTENSION IDEAS (for curious students!)
//  -------------------------------------------------------
//  1. ADD MORE THEMES:
//     Just add another object to the `themes` array at the top!
//     Give it a name, bgTop/bgBot colors, spiralColor, and particles array.
//
//  2. ADD DIFFICULTY LEVELS:
//     - Easy: maxFibNumbers = 8 (fewer steps)
//     - Hard: maxFibNumbers = 16 (more steps, larger spiral)
//     - Create buttons at the start screen to pick difficulty.
//
//  3. ADD A QUIZ MODE:
//     Instead of showing the next number, ask the player to type it.
//     Use createInput() from p5.js DOM library.
//
//  4. ADD SOUND:
//     Use the p5.sound library. Play a musical note for each Fibonacci
//     number — make each number correspond to a different pitch!
//
//  5. ANIMATE THE PETALS:
//     In the Flower Garden theme, draw actual flower petals on the
//     spiral instead of just a line. Each petal count = a Fibonacci number!
//
//  6. ADD A TIMER / HIGH SCORE:
//     Track how fast the player completes the sequence.
//     Store the best time using localStorage.
// ============================================================