class CharacterAnimation {
    constructor() {
        this.character = document.getElementById('character');
        this.characterImg = this.character.querySelector('img');
        this.speechBubble = document.getElementById('speech-bubble');
        this.x = window.innerWidth / 2;
        this.SPEED = 2;
        this.mode = "WAIT";
        this.waitStart = Date.now();
        this.walkDirection = 1;
        this.lastAnimTime = Date.now();
        this.walkDistance = 0;
        this.walkTarget = 0;
        this.ANIM_INTERVAL = 200; // 200ms
        this.WAIT_TIME_MIN = 2000; // 2秒
        this.WAIT_TIME_MAX = 5000; // 5秒

        // 画像パスの設定
        this.images = {
            front: '/static/images/char_front.png',
            side1: '/static/images/char_side1.png',
            side2: '/static/images/char_side2.png',
            right1: '/static/images/char_right1.png',
            right2: '/static/images/char_right2.png'
        };

        // 画像のプリロード
        this.loadedImages = {};
        for (let key in this.images) {
            const img = new Image();
            img.src = this.images[key];
            this.loadedImages[key] = img;
        }

        this.currentImg = this.images.front;
        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
    }

    getRandomWaitTime() {
        return Math.random() * (this.WAIT_TIME_MAX - this.WAIT_TIME_MIN) + this.WAIT_TIME_MIN;
    }

    updatePosition() {
        const containerWidth = document.querySelector('.character-area').offsetWidth;
        const characterWidth = this.characterImg.offsetWidth;
        const margin = 50; // 余白

        this.x += this.SPEED * this.walkDirection;
        this.walkDistance += this.SPEED;

        // 画面端での反転
        if (this.x < margin) {
            this.x = margin;
            this.walkDirection = 1;
        } else if (this.x > containerWidth - margin) {
            this.x = containerWidth - margin;
            this.walkDirection = -1;
        }

        // キャラクターの位置を更新
        this.character.style.transform = `translateX(${this.x - containerWidth/2}px)`;
        
        // 吹き出しも一緒に移動
        if (this.speechBubble) {
            this.speechBubble.style.transform = `translateX(${this.x - containerWidth/2 - 50}px)`;
        }
    }

    updateAnimation() {
        const now = Date.now();
        if (now - this.lastAnimTime > this.ANIM_INTERVAL) {
            if (this.walkDirection === 1) {
                this.currentImg = this.currentImg === this.images.right1 ? this.images.right2 : this.images.right1;
            } else {
                this.currentImg = this.currentImg === this.images.side1 ? this.images.side2 : this.images.side1;
            }
            this.characterImg.src = this.currentImg;
            this.lastAnimTime = now;
        }
    }

    animate() {
        const now = Date.now();

        if (this.mode === "WAIT") {
            if (now - this.waitStart > this.getRandomWaitTime()) {
                this.mode = "WALK";
                this.walkDirection = Math.random() < 0.5 ? -1 : 1;
                this.walkTarget = Math.random() * 100 + 50;
                this.walkDistance = 0;
                this.lastAnimTime = now;
                this.currentImg = this.walkDirection === 1 ? this.images.right1 : this.images.side1;
                this.characterImg.src = this.currentImg;
            }
        } else if (this.mode === "WALK") {
            this.updatePosition();
            this.updateAnimation();

            if (this.walkDistance >= this.walkTarget) {
                this.mode = "WAIT";
                this.waitStart = now;
                this.currentImg = this.images.front;
                this.characterImg.src = this.currentImg;
            }
        }

        requestAnimationFrame(this.animate);
    }
}

// DOMが読み込まれた後にアニメーションを開始
document.addEventListener('DOMContentLoaded', () => {
    new CharacterAnimation();
});