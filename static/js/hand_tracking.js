/**
 * Hand tracking module using MediaPipe Hands.
 * This provides client-side hand tracking for immediate feedback.
 */
class HandTracker {
  constructor(videoElement, canvasElement) {
      this.videoElement = videoElement;
      this.canvasElement = canvasElement;
      this.canvasCtx = canvasElement.getContext('2d');
      this.landmarks = [];
      this.isTracking = false;
      this.hands = null;
      this.camera = null;
      this.onResultsCallbacks = [];
  }

  /**
   * Initialize the MediaPipe Hands solution.
   */
  async initialize() {
      if (!window.Hands) {
          console.error('MediaPipe Hands library not loaded');
          return false;
      }

      try {
          // Initialize MediaPipe Hands
          this.hands = new Hands({
              locateFile: (file) => {
                  return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
              }
          });

          // Set options
          await this.hands.setOptions({
              maxNumHands: 2,
              modelComplexity: 1,
              minDetectionConfidence: 0.5,
              minTrackingConfidence: 0.5
          });

          // Set up callback
          this.hands.onResults((results) => {
              this.onResults(results);
          });

          console.log('MediaPipe Hands initialized successfully');
          return true;
      } catch (error) {
          console.error('Error initializing MediaPipe Hands:', error);
          return false;
      }
  }

  /**
   * Start hand tracking.
   */
  async start() {
      if (!this.hands) {
          const initialized = await this.initialize();
          if (!initialized) return false;
      }

      // Create a camera object
      this.camera = new Camera(this.videoElement, {
          onFrame: async () => {
              await this.hands.send({ image: this.videoElement });
          },
          width: 640,
          height: 480
      });

      // Start the camera
      await this.camera.start();
      this.isTracking = true;
      return true;
  }

  /**
   * Stop hand tracking.
   */
  stop() {
      if (this.camera) {
          this.camera.stop();
          this.isTracking = false;
      }
  }

  /**
   * Process hand tracking results.
   */
  onResults(results) {
      // Clear canvas
      this.canvasCtx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height);

      // Store landmarks
      this.landmarks = results.multiHandLandmarks || [];

      // Draw landmarks and connections
      if (this.landmarks.length > 0) {
          this.drawLandmarks();
      }

      // Call registered callbacks
      this.onResultsCallbacks.forEach(callback => callback(results));
  }

  /**
   * Draw hand landmarks on the canvas.
   */
  drawLandmarks() {
      // Define connections between landmarks for hand
      const connections = [
          [0, 1], [1, 2], [2, 3], [3, 4],  // Thumb
          [0, 5], [5, 6], [6, 7], [7, 8],  // Index finger
          [0, 9], [9, 10], [10, 11], [11, 12],  // Middle finger
          [0, 13], [13, 14], [14, 15], [15, 16],  // Ring finger
          [0, 17], [17, 18], [18, 19], [19, 20],  // Pinky
          [0, 5], [5, 9], [9, 13], [13, 17]  // Palm
      ];

      this.landmarks.forEach(handLandmarks => {
          // Draw each landmark as a circle
          handLandmarks.forEach((landmark, index) => {
              const x = landmark.x * this.canvasElement.width;
              const y = landmark.y * this.canvasElement.height;

              this.canvasCtx.beginPath();
              this.canvasCtx.arc(x, y, 5, 0, 2 * Math.PI);
              this.canvasCtx.fillStyle = index === 0 ? 'rgba(255, 0, 0, 0.7)' : 'rgba(0, 255, 0, 0.7)';
              this.canvasCtx.fill();
          });

          // Draw connections between landmarks
          this.canvasCtx.lineWidth = 3;
          this.canvasCtx.strokeStyle = 'rgba(0, 255, 0, 0.7)';

          connections.forEach(([start, end]) => {
              if (handLandmarks[start] && handLandmarks[end]) {
                  const startX = handLandmarks[start].x * this.canvasElement.width;
                  const startY = handLandmarks[start].y * this.canvasElement.height;
                  const endX = handLandmarks[end].x * this.canvasElement.width;
                  const endY = handLandmarks[end].y * this.canvasElement.height;

                  this.canvasCtx.beginPath();
                  this.canvasCtx.moveTo(startX, startY);
                  this.canvasCtx.lineTo(endX, endY);
                  this.canvasCtx.stroke();
              }
          });
      });
  }

  /**
   * Register a callback for hand tracking results.
   */
  onResultsCallback(callback) {
      if (typeof callback === 'function') {
          this.onResultsCallbacks.push(callback);
      }
  }

  /**
   * Check if hands are currently detected.
   */
  handsDetected() {
      return this.landmarks.length > 0;
  }

  /**
   * Get the current hand landmarks.
   */
  getLandmarks() {
      return this.landmarks;
  }
}

// Export the class
window.HandTracker = HandTracker;
