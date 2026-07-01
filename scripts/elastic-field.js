(function() {
  'use strict';

  var canvas = document.getElementById('elastic-field');
  var readout = document.querySelector('.field-readout');

  if (!canvas) {
    return;
  }

  var context = canvas.getContext && canvas.getContext('2d', { alpha: true });
  if (!context) {
    canvas.hidden = true;
    if (readout) {
      readout.hidden = true;
    }
    return;
  }

  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  var saveData = navigator.connection && navigator.connection.saveData;
  var cellSize = 32;
  var fixedStep = 1000 / 30;
  var width = 0;
  var height = 0;
  var pixelRatio = 1;
  var columns = 0;
  var rows = 0;
  var fieldSize = 0;
  var displacement;
  var velocity;
  var nextDisplacement;
  var nextVelocity;
  var animationFrame = 0;
  var resizeFrame = 0;
  var running = false;
  var lastFrameTime = 0;
  var accumulator = 0;
  var quietFrames = 0;
  var pendingImpulse = null;
  var lastPointer = null;
  var lastReadoutTime = 0;
  var contourPoints = new Float32Array(8);
  var readoutValue = readout && readout.querySelector('.field-readout__value');

  var contourLevels = [
    { value: -0.06, color: 'rgba(140, 21, 21, 0.24)', width: 1.05 },
    { value: -0.02, color: 'rgba(140, 21, 21, 0.13)', width: 0.75 },
    { value: 0.02, color: 'rgba(23, 107, 103, 0.14)', width: 0.75 },
    { value: 0.06, color: 'rgba(23, 107, 103, 0.25)', width: 1.05 }
  ];

  function shouldDisable() {
    return reducedMotion.matches ||
      !finePointer.matches ||
      saveData ||
      window.innerWidth < 900;
  }

  function stop() {
    running = false;
    if (animationFrame) {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = 0;
    }
  }

  function setFieldVisibility(disabled) {
    canvas.hidden = disabled;
    if (readout) {
      readout.hidden = disabled;
    }
    document.documentElement.classList.toggle('elastic-field-disabled', disabled);
    if (disabled) {
      stop();
    }
  }

  function resetField() {
    columns = Math.ceil(width / cellSize) + 1;
    rows = Math.ceil(height / cellSize) + 1;
    fieldSize = columns * rows;
    displacement = new Float32Array(fieldSize);
    velocity = new Float32Array(fieldSize);
    nextDisplacement = new Float32Array(fieldSize);
    nextVelocity = new Float32Array(fieldSize);
    pendingImpulse = null;
    lastPointer = null;
    quietFrames = 0;
    context.clearRect(0, 0, width, height);
    updateReadout(0, true);
  }

  function configure() {
    if (shouldDisable()) {
      setFieldVisibility(true);
      return;
    }

    setFieldVisibility(false);
    stop();
    width = window.innerWidth;
    height = window.innerHeight;
    pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(height * pixelRatio);
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    resetField();

    if (width >= 1360) {
      applyDipole(width - 112, Math.min(height * 0.28, 280), -1, 0.2, 0.045);
      start();
    }
  }

  function clamp(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, value));
  }

  function applyDipole(x, y, directionX, directionY, amplitude) {
    if (!velocity) {
      return;
    }

    var gridX = x / cellSize;
    var gridY = y / cellSize;
    var sigma = 1.6;
    var radius = Math.ceil(sigma * 3);
    var minimumX = Math.max(1, Math.floor(gridX) - radius);
    var maximumX = Math.min(columns - 2, Math.ceil(gridX) + radius);
    var minimumY = Math.max(1, Math.floor(gridY) - radius);
    var maximumY = Math.min(rows - 2, Math.ceil(gridY) + radius);
    var xIndex;
    var yIndex;

    for (yIndex = minimumY; yIndex <= maximumY; yIndex += 1) {
      for (xIndex = minimumX; xIndex <= maximumX; xIndex += 1) {
        var offsetX = xIndex - gridX;
        var offsetY = yIndex - gridY;
        var distanceSquared = offsetX * offsetX + offsetY * offsetY;
        var projection = (offsetX * directionX + offsetY * directionY) / sigma;
        var weight = Math.exp(-distanceSquared / (2 * sigma * sigma));
        var index = yIndex * columns + xIndex;
        velocity[index] = clamp(
          velocity[index] + amplitude * projection * weight,
          -0.25,
          0.25
        );
      }
    }
  }

  function updateSimulation() {
    nextDisplacement.fill(0);
    nextVelocity.fill(0);
    var maximumDisplacement = 0;
    var maximumVelocity = 0;
    var x;
    var y;

    for (y = 1; y < rows - 1; y += 1) {
      for (x = 1; x < columns - 1; x += 1) {
        var index = y * columns + x;
        var current = displacement[index];
        var laplacian =
          displacement[index - 1] +
          displacement[index + 1] +
          displacement[index - columns] +
          displacement[index + columns] -
          4 * current;
        var edgeDistance = Math.min(x, y, columns - 1 - x, rows - 1 - y);
        var damping = edgeDistance < 4
          ? 0.9 + (edgeDistance / 4) * (0.982 - 0.9)
          : 0.982;
        var nextV = (velocity[index] + 0.085 * laplacian - 0.001 * current) * damping;
        var nextU = current + nextV;

        nextV = clamp(nextV, -0.25, 0.25);
        nextU = clamp(nextU, -0.42, 0.42);
        nextVelocity[index] = nextV;
        nextDisplacement[index] = nextU;
        maximumDisplacement = Math.max(maximumDisplacement, Math.abs(nextU));
        maximumVelocity = Math.max(maximumVelocity, Math.abs(nextV));
      }
    }

    var swap = displacement;
    displacement = nextDisplacement;
    nextDisplacement = swap;
    swap = velocity;
    velocity = nextVelocity;
    nextVelocity = swap;

    return {
      displacement: maximumDisplacement,
      velocity: maximumVelocity
    };
  }

  function addContourPoint(pointIndex, x, y) {
    contourPoints[pointIndex * 2] = x;
    contourPoints[pointIndex * 2 + 1] = y;
  }

  function drawSegment(first, second) {
    context.moveTo(contourPoints[first * 2], contourPoints[first * 2 + 1]);
    context.lineTo(contourPoints[second * 2], contourPoints[second * 2 + 1]);
  }

  function drawContour(level) {
    context.beginPath();
    var x;
    var y;

    for (y = 0; y < rows - 1; y += 1) {
      for (x = 0; x < columns - 1; x += 1) {
        var topLeft = displacement[y * columns + x];
        var topRight = displacement[y * columns + x + 1];
        var bottomLeft = displacement[(y + 1) * columns + x];
        var bottomRight = displacement[(y + 1) * columns + x + 1];
        var pointCount = 0;
        var ratio;

        if ((topLeft > level) !== (topRight > level)) {
          ratio = (level - topLeft) / (topRight - topLeft);
          addContourPoint(pointCount, (x + ratio) * cellSize, y * cellSize);
          pointCount += 1;
        }
        if ((topRight > level) !== (bottomRight > level)) {
          ratio = (level - topRight) / (bottomRight - topRight);
          addContourPoint(pointCount, (x + 1) * cellSize, (y + ratio) * cellSize);
          pointCount += 1;
        }
        if ((bottomLeft > level) !== (bottomRight > level)) {
          ratio = (level - bottomLeft) / (bottomRight - bottomLeft);
          addContourPoint(pointCount, (x + ratio) * cellSize, (y + 1) * cellSize);
          pointCount += 1;
        }
        if ((topLeft > level) !== (bottomLeft > level)) {
          ratio = (level - topLeft) / (bottomLeft - topLeft);
          addContourPoint(pointCount, x * cellSize, (y + ratio) * cellSize);
          pointCount += 1;
        }

        if (pointCount === 2) {
          drawSegment(0, 1);
        } else if (pointCount === 4) {
          var center = (topLeft + topRight + bottomLeft + bottomRight) * 0.25;
          if ((center > level) === (topLeft > level)) {
            drawSegment(0, 1);
            drawSegment(2, 3);
          } else {
            drawSegment(0, 3);
            drawSegment(1, 2);
          }
        }
      }
    }

    context.stroke();
  }

  function drawContours() {
    context.clearRect(0, 0, width, height);
    context.lineCap = 'round';
    context.lineJoin = 'round';

    contourLevels.forEach(function(level) {
      context.strokeStyle = level.color;
      context.lineWidth = level.width;
      drawContour(level.value);
    });
  }

  function updateReadout(maximumDisplacement, force) {
    if (!readout) {
      return;
    }

    var now = performance.now();
    if (!force && now - lastReadoutTime < 80) {
      return;
    }

    lastReadoutTime = now;
    var energy = clamp(maximumDisplacement / 0.1, 0, 1);
    readout.style.setProperty('--field-energy', energy.toFixed(3));
    if (readoutValue) {
      readoutValue.textContent = 'ε ' + energy.toFixed(2);
    }
  }

  function frame(now) {
    animationFrame = 0;
    if (!running || document.hidden || shouldDisable()) {
      stop();
      return;
    }

    if (!lastFrameTime) {
      lastFrameTime = now;
    }
    accumulator += Math.min(now - lastFrameTime, fixedStep * 2);
    lastFrameTime = now;

    if (pendingImpulse) {
      applyDipole(
        pendingImpulse.x,
        pendingImpulse.y,
        pendingImpulse.directionX,
        pendingImpulse.directionY,
        pendingImpulse.amplitude
      );
      pendingImpulse = null;
    }

    var state = { displacement: 0, velocity: 0 };
    var steps = 0;
    while (accumulator >= fixedStep && steps < 2) {
      state = updateSimulation();
      accumulator -= fixedStep;
      steps += 1;
    }
    if (steps === 2 && accumulator >= fixedStep) {
      accumulator = 0;
    }

    if (steps > 0) {
      drawContours();
      updateReadout(state.displacement, false);
      if (state.displacement < 0.007 && state.velocity < 0.001) {
        quietFrames += 1;
      } else {
        quietFrames = 0;
      }
    }

    if (quietFrames >= 18) {
      displacement.fill(0);
      velocity.fill(0);
      context.clearRect(0, 0, width, height);
      updateReadout(0, true);
      running = false;
      return;
    }

    animationFrame = window.requestAnimationFrame(frame);
  }

  function start() {
    if (running || shouldDisable()) {
      return;
    }
    running = true;
    lastFrameTime = performance.now();
    accumulator = fixedStep;
    animationFrame = window.requestAnimationFrame(frame);
  }

  function handlePointerMove(event) {
    if (shouldDisable() || (event.pointerType && event.pointerType === 'touch')) {
      return;
    }

    var now = performance.now();
    if (lastPointer && now - lastPointer.time < 180) {
      var movementX = event.clientX - lastPointer.x;
      var movementY = event.clientY - lastPointer.y;
      var distance = Math.sqrt(movementX * movementX + movementY * movementY);

      if (distance > 0.8) {
        pendingImpulse = {
          x: event.clientX,
          y: event.clientY,
          directionX: movementX / distance,
          directionY: movementY / distance,
          amplitude: 0.035 + Math.min(distance / 40, 1) * 0.045
        };
        document.body.classList.add('field-engaged');
        start();
      }
    }

    lastPointer = {
      x: event.clientX,
      y: event.clientY,
      time: now
    };
  }

  function scheduleConfigure() {
    if (resizeFrame) {
      window.cancelAnimationFrame(resizeFrame);
    }
    resizeFrame = window.requestAnimationFrame(function() {
      resizeFrame = 0;
      configure();
    });
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      stop();
    } else if (!shouldDisable() && displacement) {
      start();
    }
  }

  window.addEventListener('pointermove', handlePointerMove, { passive: true });
  window.addEventListener('resize', scheduleConfigure, { passive: true });
  document.addEventListener('mouseleave', function() {
    lastPointer = null;
  });
  document.addEventListener('visibilitychange', handleVisibilityChange);

  if (reducedMotion.addEventListener) {
    reducedMotion.addEventListener('change', configure);
    finePointer.addEventListener('change', configure);
  } else {
    reducedMotion.addListener(configure);
    finePointer.addListener(configure);
  }

  configure();
})();
