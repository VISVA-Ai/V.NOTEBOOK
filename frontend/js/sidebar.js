/**
 * Sidebar Collapse Manager
 * Handles collapsing left/right sidebars to icon-only mode
 */
const SidebarUI = {
    leftCollapsed: false,
    rightCollapsed: false,

    init() {
        // Add collapse buttons to sidebars
        this.addCollapseButtons();
        this.bindEvents();
    },

    addCollapseButtons() {
        // Left sidebar collapse button
        const leftCol = document.querySelector('.col-left');
        if (leftCol) {
            const btn = document.createElement('button');
            btn.className = 'sidebar-collapse-btn';
            btn.innerHTML = '◀';
            btn.title = 'Collapse sidebar';
            btn.onclick = () => this.toggleLeft();
            leftCol.prepend(btn);
        }

        // Right sidebar collapse button  
        const rightCol = document.querySelector('.col-right');
        if (rightCol) {
            const btn = document.createElement('button');
            btn.className = 'sidebar-collapse-btn';
            btn.innerHTML = '▶';
            btn.title = 'Collapse sidebar';
            btn.onclick = () => this.toggleRight();
            rightCol.prepend(btn);
        }
    },

    bindEvents() {
        // State persistence
        const savedLeft = localStorage.getItem('sidebar_left_collapsed');
        const savedRight = localStorage.getItem('sidebar_right_collapsed');

        if (savedLeft === 'true') this.toggleLeft(false);
        if (savedRight === 'true') this.toggleRight(false);
    },

    toggleLeft(save = true) {
        const leftCol = document.querySelector('.col-left');
        const gridLayout = document.querySelector('.grid-layout');
        const btn = leftCol?.querySelector('.sidebar-collapse-btn');

        if (!leftCol || !gridLayout) return;

        this.leftCollapsed = !this.leftCollapsed;

        if (this.leftCollapsed) {
            leftCol.classList.add('collapsed');
            gridLayout.classList.add('left-collapsed');
            if (btn) btn.innerHTML = '▶';
        } else {
            leftCol.classList.remove('collapsed');
            gridLayout.classList.remove('left-collapsed');
            if (btn) btn.innerHTML = '◀';
        }

        if (save) {
            localStorage.setItem('sidebar_left_collapsed', this.leftCollapsed);
        }
    },

    toggleRight(save = true) {
        const rightCol = document.querySelector('.col-right');
        const gridLayout = document.querySelector('.grid-layout');
        const btn = rightCol?.querySelector('.sidebar-collapse-btn');

        if (!rightCol || !gridLayout) return;

        this.rightCollapsed = !this.rightCollapsed;

        if (this.rightCollapsed) {
            rightCol.classList.add('collapsed');
            gridLayout.classList.add('right-collapsed');
            if (btn) btn.innerHTML = '◀';
        } else {
            rightCol.classList.remove('collapsed');
            gridLayout.classList.remove('right-collapsed');
            if (btn) btn.innerHTML = '▶';
        }

        if (save) {
            localStorage.setItem('sidebar_right_collapsed', this.rightCollapsed);
        }
    }
};

window.SidebarUI = SidebarUI;

// Init on load
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => SidebarUI.init(), 100);
});
