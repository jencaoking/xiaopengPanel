<template>
  <div class="app-wrapper">
    <!-- 动态背景光斑 - 为玻璃态效果提供深度 -->
    <div class="ios-bg-orbs" aria-hidden="true">
      <div class="ios-bg-orb ios-bg-orb-1"></div>
      <div class="ios-bg-orb ios-bg-orb-2"></div>
      <div class="ios-bg-orb ios-bg-orb-3"></div>
    </div>

    <!-- 登录状态：显示主应用 -->
    <template v-if="isLoggedIn">
      <!-- 移动端遮罩层 -->
      <div 
        v-if="isMobileSidebarOpen" 
        class="mobile-overlay"
        @click="closeMobileSidebar"
      ></div>
      
      <!-- 侧边栏导航 -->
      <aside 
        class="app-sidebar"
        :class="{ 
          'sidebar-collapsed': isSidebarCollapsed,
          'sidebar-mobile-open': isMobileSidebarOpen 
        }"
        role="navigation"
        aria-label="主导航"
      >
        <!-- Logo区域 -->
        <div class="sidebar-brand">
          <div class="brand-logo">
            <svg viewBox="0 0 32 32" class="logo-icon" aria-hidden="true">
              <defs>
                <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style="stop-color:#667eea"/>
                  <stop offset="100%" style="stop-color:#764ba2"/>
                </linearGradient>
              </defs>
              <rect x="2" y="2" width="12" height="12" rx="3" fill="url(#logoGradient)" opacity="0.9"/>
              <rect x="18" y="2" width="12" height="12" rx="3" fill="url(#logoGradient)" opacity="0.7"/>
              <rect x="2" y="18" width="12" height="12" rx="3" fill="url(#logoGradient)" opacity="0.7"/>
              <rect x="18" y="18" width="12" height="12" rx="3" fill="url(#logoGradient)" opacity="0.5"/>
            </svg>
          </div>
          <span class="brand-text" v-show="!isSidebarCollapsed">{{ $t('common.systemInfo') }}</span>
          <button 
            class="sidebar-toggle-btn"
            @click="toggleSidebar"
            :title="isSidebarCollapsed ? $t('common.expand') : $t('common.collapse')"
            aria-label="切换侧边栏"
          >
            <svg viewBox="0 0 24 24" class="toggle-icon" :class="{ 'rotated': isSidebarCollapsed }">
              <path fill="currentColor" d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
            </svg>
          </button>
        </div>

        <!-- 导航菜单 -->
        <nav class="sidebar-nav" role="menubar">
          <ul class="nav-list">
            <li 
              v-for="item in navItems" 
              :key="item.page"
              class="nav-item-wrapper"
              role="none"
            >
              <button
                class="nav-item"
                :class="{ 'active': currentPage === item.page }"
                @click="handleNavClick(item.page)"
                role="menuitem"
                :aria-current="currentPage === item.page ? 'page' : null"
              >
                <span class="nav-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" class="icon-svg">
                    <path :d="item.iconPath" fill="currentColor"/>
                  </svg>
                </span>
                <span class="nav-text" v-show="!isSidebarCollapsed">{{ item.text }}</span>
                <span class="nav-indicator" v-if="currentPage === item.page"></span>
              </button>
            </li>
          </ul>
        </nav>

        <!-- 侧边栏底部 -->
        <div class="sidebar-footer">
          <button 
            class="logout-btn"
            @click="handleLogout"
            :title="$t('common.logout')"
          >
            <span class="logout-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" class="icon-svg">
                <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" fill="currentColor"/>
              </svg>
            </span>
            <span class="logout-text" v-show="!isSidebarCollapsed">{{ $t('common.logout') }}</span>
          </button>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main class="app-main" role="main">
        <!-- 顶部导航栏 -->
        <header class="app-header">
          <!-- 移动端菜单按钮 -->
          <button 
            class="mobile-menu-btn"
            @click="openMobileSidebar"
            aria-label="打开菜单"
          >
            <svg viewBox="0 0 24 24" class="icon-svg">
              <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z" fill="currentColor"/>
            </svg>
          </button>

          <!-- 页面标题 -->
          <h1 class="page-title">{{ pageTitle }}</h1>

          <!-- 右侧控制区 -->
          <div class="header-controls">
            <!-- 搜索框 -->
            <div class="search-box" :class="{ 'search-expanded': isSearchExpanded }">
              <button 
                class="search-toggle"
                @click="toggleSearch"
                aria-label="搜索"
              >
                <svg viewBox="0 0 24 24" class="icon-svg">
                  <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" fill="currentColor"/>
                </svg>
              </button>
              <input 
                v-if="isSearchExpanded"
                v-model="searchQuery"
                type="text"
                class="search-input"
                :placeholder="$t('common.search')"
                @blur="closeSearch"
                ref="searchInput"
              />
            </div>

            <!-- 主题切换 -->
            <div class="theme-dropdown">
              <button 
                class="control-btn theme-toggle"
                @click="toggleThemeDropdown"
                :title="$t('common.theme')"
                aria-haspopup="true"
                :aria-expanded="isThemeDropdownOpen"
              >
                <svg v-if="isDarkTheme" viewBox="0 0 24 24" class="icon-svg">
                  <path d="M20 8.69V4h-4.69L12 .69 8.69 4H4v4.69L.69 12 4 15.31V20h4.69L12 23.31 15.31 20H20v-4.69L23.31 12 20 8.69zM12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6 6 2.69 6 6-2.69 6-6 6zm0-10c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4z" fill="currentColor"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" class="icon-svg">
                  <path d="M9 2c-1.05 0-2.05.16-3 .46 1.69 1.24 2.79 3.26 2.79 5.54 0 3.87-3.13 7-7 7-1.06 0-2.06-.24-2.98-.66C.95 16.42 4.5 20 9 20c5.52 0 10-4.48 10-10S14.52 2 9 2z" fill="currentColor"/>
                </svg>
              </button>
              <transition name="dropdown">
                <div 
                  v-if="isThemeDropdownOpen" 
                  class="dropdown-menu theme-menu"
                  @click.stop
                >
                  <div class="dropdown-header">{{ $t('common.selectTheme') }}</div>
                  <button
                    v-for="themeItem in themeList"
                    :key="themeItem.id"
                    class="dropdown-item theme-item"
                    :class="{ active: currentTheme === themeItem.id }"
                    @click="changeTheme(themeItem.id)"
                  >
                    <span class="theme-preview" :style="{ background: themeItem.previewBg }">
                      <span class="theme-dot" :style="{ background: themeItem.accentColor }"></span>
                    </span>
                    <span class="theme-name">{{ $t('themes.' + themeItem.id) }}</span>
                    <svg v-if="currentTheme === themeItem.id" class="theme-check" viewBox="0 0 24 24" fill="none">
                      <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </button>
                </div>
              </transition>
            </div>

            <!-- 语言切换 -->
            <div class="language-dropdown">
              <button 
                class="control-btn language-btn"
                @click="toggleLanguageDropdown"
                :title="$t('common.language')"
                aria-haspopup="true"
                :aria-expanded="isLanguageDropdownOpen"
              >
                <svg viewBox="0 0 24 24" class="icon-svg">
                  <path d="M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z" fill="currentColor"/>
                </svg>
                <span class="language-code">{{ currentLanguage.toUpperCase() }}</span>
              </button>
              <transition name="dropdown">
                <div 
                  v-if="isLanguageDropdownOpen" 
                  class="dropdown-menu"
                  role="menu"
                >
                  <button 
                    v-for="lang in availableLanguages"
                    :key="lang.code"
                    class="dropdown-item"
                    :class="{ 'active': currentLanguage === lang.code }"
                    @click="changeLanguage(lang.code)"
                    role="menuitem"
                  >
                    <span class="lang-flag">{{ lang.flag }}</span>
                    <span class="lang-name">{{ lang.name }}</span>
                  </button>
                </div>
              </transition>
            </div>

            <!-- 用户菜单 -->
            <div class="user-menu">
              <button 
                class="user-btn"
                @click="toggleUserMenu"
                aria-haspopup="true"
                :aria-expanded="isUserMenuOpen"
              >
                <div class="user-avatar">
                  {{ userInitials }}
                </div>
                <span class="user-name" v-if="!isMobile">{{ username }}</span>
                <svg viewBox="0 0 24 24" class="dropdown-icon" :class="{ 'rotated': isUserMenuOpen }">
                  <path d="M7 10l5 5 5-5z" fill="currentColor"/>
                </svg>
              </button>
              <transition name="dropdown">
                <div 
                  v-if="isUserMenuOpen" 
                  class="dropdown-menu user-dropdown"
                  role="menu"
                >
                  <div class="dropdown-header">
                    <div class="user-avatar large">{{ userInitials }}</div>
                    <div class="user-info">
                      <span class="user-fullname">{{ username }}</span>
                      <span class="user-role">{{ $t('common.admin') }}</span>
                    </div>
                  </div>
                  <div class="dropdown-divider"></div>
                  <button class="dropdown-item" @click="goToProfile" role="menuitem">
                    <svg viewBox="0 0 24 24" class="item-icon">
                      <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" fill="currentColor"/>
                    </svg>
                    {{ $t('common.profile') }}
                  </button>
                  <button class="dropdown-item" @click="goToSettings" role="menuitem">
                    <svg viewBox="0 0 24 24" class="item-icon">
                      <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L5.04 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" fill="currentColor"/>
                    </svg>
                    {{ $t('common.settings') }}
                  </button>
                  <div class="dropdown-divider"></div>
                  <button class="dropdown-item danger" @click="handleLogout" role="menuitem">
                    <svg viewBox="0 0 24 24" class="item-icon">
                      <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" fill="currentColor"/>
                    </svg>
                    {{ $t('common.logout') }}
                  </button>
                </div>
              </transition>
            </div>
          </div>
        </header>

        <!-- 页面内容区 -->
        <div class="page-content">
          <transition name="page" mode="out-in">
            <component 
              :is="currentComponent" 
              :key="currentPage"
            />
          </transition>
        </div>
      </main>

      <!-- AI 助手浮动组件 -->
      <AIAssistant />
    </template>

    <!-- 未登录状态：显示登录页 -->
    <Login v-else />
  </div>
</template>

<script>
import { computed, ref, watch, onMounted, onUnmounted, shallowRef } from 'vue'
import { useStore } from 'vuex'
import { useI18n } from 'vue-i18n'

// 导入页面组件
import Dashboard from './components/DashboardEnhanced.vue'
import Processes from './components/Processes.vue'
import Services from './components/Services.vue'
import Logs from './components/Logs.vue'
import Config from './components/Config.vue'
import Users from './components/Users.vue'
import FileManager from './components/FileManager.vue'
import Sites from './components/Sites.vue'
import WebService from './components/WebService.vue'
import Databases from './components/Databases.vue'
import Terminal from './components/Terminal.vue'
import CodeEditor from './components/CodeEditor.vue'
import Firewall from './components/Firewall.vue'
import TwoFactorAuth from './components/TwoFactorAuth.vue'
import CronManager from './components/CronManager.vue'
import Roles from './components/Roles.vue'
import AIAssistant from './components/AIAssistant.vue'
import Login from './components/LoginModern.vue'

// 组件映射
const componentMap = {
  dashboard: Dashboard,
  processes: Processes,
  services: Services,
  logs: Logs,
  config: Config,
  users: Users,
  roles: Roles,
  'file-manager': FileManager,
  sites: Sites,
  'web-service': WebService,
  databases: Databases,
  terminal: Terminal,
  editor: CodeEditor,
  firewall: Firewall,
  'two-factor': TwoFactorAuth,
  cron: CronManager
}

// 导航图标SVG路径
const iconPaths = {
  dashboard: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z',
  processes: 'M15 1H9v2h6V1zm-4 13h2V8h-2v6zm8.03-6.61l1.42-1.42c-.43-.51-.9-.99-1.41-1.41l-1.42 1.42C16.07 4.74 14.12 4 12 4c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-2.12-.74-4.07-1.97-5.61zM12 20c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z',
  services: 'M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z',
  logs: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z',
  config: 'M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L5.04 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z',
  users: 'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z',
  'file-manager': 'M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V8h16v10z',
  sites: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z',
  'web-service': 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z',
  databases: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z',
  terminal: 'M20 19V7H4v12h16m0-16a2 2 0 012 2v14a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h16M7.5 13h2v2h-2v-2m0-4h2v2h-2V9m4 4h2v2h-2v-2m0-4h2v2h-2V9m4 4h2v2h-2v-2m0-4h2v2h-2V9z',
  editor: 'M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z',
  firewall: 'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z',
  'two-factor': 'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-1 14l-2-2 1.41-1.41L11 12.17l4.59-4.59L17 9l-6 6z',
  cron: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z',
  roles: 'M12 2l-5.5 2.5v6c0 3.5 2.5 6.5 5.5 7.5 3-1 5.5-4 5.5-7.5v-6L12 2zm0 2.18l3.5 1.59v4.73c0 2.5-1.5 4.5-3.5 5.4-2-.9-3.5-2.9-3.5-5.4V5.77L12 4.18zM5 13c0 4.97 4.03 9 9 9v-2c-3.87 0-7-3.13-7-7H5z'
}

export default {
  name: 'App',
  components: {
    Dashboard,
    Processes,
    Services,
    Logs,
    Config,
    Users,
    FileManager,
    Sites,
    WebService,
    Databases,
    Terminal,
    CodeEditor,
    Firewall,
    TwoFactorAuth,
    CronManager,
    Roles,
    AIAssistant,
    Login
  },
  setup() {
    const store = useStore()
    const { t, locale } = useI18n()
    
    // 响应式状态
    const isSearchExpanded = ref(false)
    const searchQuery = ref('')
    const searchInput = ref(null)
    const isLanguageDropdownOpen = ref(false)
    const isThemeDropdownOpen = ref(false)
    const isUserMenuOpen = ref(false)
    const isMobileSidebarOpen = ref(false)
    const isMobile = ref(false)

    // 触摸手势状态（侧边栏滑动开关）
    const touchStartX = ref(0)
    const touchStartY = ref(0)
    const touchCurrentX = ref(0)
    const isSwiping = ref(false)
    const swipeThreshold = 50 // 触发滑动开关的最小距离
    const edgeThreshold = 30 // 屏幕边缘触发区域宽度

    // 计算属性
    const isLoggedIn = computed(() => store.getters.isLoggedIn)
    const currentPage = computed(() => store.state.currentPage)
    const isSidebarCollapsed = computed(() => !store.state.sidebarOpen)
    const isDarkTheme = computed(() => store.state.theme === 'dark')
    const currentTheme = computed(() => store.state.theme)
    const currentLanguage = computed(() => store.state.language)
    const username = computed(() => store.state.user?.username || t('common.admin'))
    const userInitials = computed(() => {
      const name = username.value
      return name.charAt(0).toUpperCase()
    })

    const currentComponent = computed(() => componentMap[currentPage.value] || Dashboard)

    const pageTitle = computed(() => {
      const titles = {
        dashboard: t('common.dashboard'),
        processes: t('common.processes'),
        services: t('common.services'),
        terminal: t('common.terminal'),
        editor: t('common.editor'),
        logs: t('common.logs'),
        config: t('common.config'),
        users: t('common.users'),
        roles: t('common.roles'),
        'file-manager': t('common.fileManager'),
        sites: t('common.sites'),
        'web-service': t('common.webService'),
        databases: t('common.databases'),
        firewall: t('common.firewall'),
        cron: t('common.cron')
      }
      return titles[currentPage.value] || t('common.dashboard')
    })

    // 导航项：每项关联所需权限，由 hasPermission getter 决定可见性
    // 权限为 null 表示对所有已登录用户可见（如双因素认证是用户自服务）
    const allNavItems = [
      { page: 'dashboard', iconPath: iconPaths.dashboard, text: t('common.dashboard'), permission: 'dashboard:view' },
      { page: 'processes', iconPath: iconPaths.processes, text: t('common.processes'), permission: 'process:view' },
      { page: 'services', iconPath: iconPaths.services, text: t('common.services'), permission: 'service:view' },
      { page: 'terminal', iconPath: iconPaths.terminal, text: t('common.terminal'), permission: 'terminal:execute' },
      { page: 'editor', iconPath: iconPaths.editor, text: t('common.editor'), permission: 'editor:view' },
      { page: 'logs', iconPath: iconPaths.logs, text: t('common.logs'), permission: 'log:view' },
      { page: 'config', iconPath: iconPaths.config, text: t('common.config'), permission: 'config:view' },
      { page: 'users', iconPath: iconPaths.users, text: t('common.users'), permission: 'user:view' },
      { page: 'roles', iconPath: iconPaths.roles, text: t('common.roles'), permission: 'role:view' },
      { page: 'file-manager', iconPath: iconPaths['file-manager'], text: t('common.fileManager'), permission: 'file:view' },
      { page: 'sites', iconPath: iconPaths.sites, text: t('common.sites'), permission: 'site:view' },
      { page: 'web-service', iconPath: iconPaths['web-service'], text: t('common.webService'), permission: 'web_service:view' },
      { page: 'databases', iconPath: iconPaths.databases, text: t('common.databases'), permission: 'database:view' },
      { page: 'firewall', iconPath: iconPaths.firewall, text: t('common.firewall'), permission: 'firewall:view' },
      { page: 'two-factor', iconPath: iconPaths['two-factor'], text: t('common.twoFactor'), permission: null },
      { page: 'cron', iconPath: iconPaths.cron, text: t('common.cron'), permission: 'cron:view' }
    ]

    const navItems = computed(() => {
      const hasPermission = store.getters.hasPermission
      return allNavItems.filter(item => !item.permission || hasPermission(item.permission))
    })

    const availableLanguages = [
      { code: 'zh', name: t('common.chinese'), flag: '🇨🇳' },
      { code: 'tw', name: t('common.traditionalChinese'), flag: '🇹🇼' },
      { code: 'en', name: t('common.english'), flag: '🇺🇸' }
    ]

    const themeList = [
      { id: 'dark', previewBg: 'linear-gradient(135deg, #000000, #1C1C1E)', accentColor: '#007AFF' },
      { id: 'light', previewBg: 'linear-gradient(135deg, #FFFFFF, #F2F2F7)', accentColor: '#007AFF' },
      { id: 'midnight', previewBg: 'linear-gradient(135deg, #0A0E27, #1A2347)', accentColor: '#0A84FF' },
      { id: 'sunset', previewBg: 'linear-gradient(135deg, #1A0F0A, #3A2418)', accentColor: '#FF9500' },
      { id: 'ocean', previewBg: 'linear-gradient(135deg, #041824, #103248)', accentColor: '#5AC8FA' },
      { id: 'forest', previewBg: 'linear-gradient(135deg, #081511, #162B22)', accentColor: '#34C759' },
      { id: 'rose', previewBg: 'linear-gradient(135deg, #1A0815, #3A1828)', accentColor: '#FF2D55' },
      { id: 'carbon', previewBg: 'linear-gradient(135deg, #0D0D0D, #262626)', accentColor: '#8E8E93' }
    ]

    // 方法
    const toggleSidebar = () => {
      store.commit('toggleSidebar')
    }

    const handleNavClick = (page) => {
      store.commit('setCurrentPage', page)
      closeMobileSidebar()
    }

    const handleLogout = () => {
      closeAllDropdowns()
      store.dispatch('logout')
    }

    const toggleTheme = () => {
      store.commit('toggleTheme')
    }

    const toggleThemeDropdown = () => {
      isThemeDropdownOpen.value = !isThemeDropdownOpen.value
      if (isThemeDropdownOpen.value) {
        isLanguageDropdownOpen.value = false
        isUserMenuOpen.value = false
      }
    }

    const changeTheme = (theme) => {
      store.commit('setTheme', theme)
      isThemeDropdownOpen.value = false
    }

    const toggleSearch = () => {
      isSearchExpanded.value = !isSearchExpanded.value
      if (isSearchExpanded.value) {
        setTimeout(() => {
          searchInput.value?.focus()
        }, 100)
      }
    }

    const closeSearch = () => {
      if (!searchQuery.value) {
        isSearchExpanded.value = false
      }
    }

    const toggleLanguageDropdown = () => {
      isLanguageDropdownOpen.value = !isLanguageDropdownOpen.value
      isThemeDropdownOpen.value = false
      isUserMenuOpen.value = false
    }

    const changeLanguage = (lang) => {
      store.commit('setLanguage', lang)
      locale.value = lang
      isLanguageDropdownOpen.value = false
    }

    const toggleUserMenu = () => {
      isUserMenuOpen.value = !isUserMenuOpen.value
      isLanguageDropdownOpen.value = false
      isThemeDropdownOpen.value = false
    }

    const closeAllDropdowns = () => {
      isLanguageDropdownOpen.value = false
      isThemeDropdownOpen.value = false
      isUserMenuOpen.value = false
    }

    const openMobileSidebar = () => {
      isMobileSidebarOpen.value = true
    }

    const closeMobileSidebar = () => {
      isMobileSidebarOpen.value = false
    }

    // 触摸手势处理：侧边栏左滑打开、右滑关闭
    const handleTouchStart = (event) => {
      if (!isMobile.value) return
      const touch = event.touches[0]
      touchStartX.value = touch.clientX
      touchStartY.value = touch.clientY
      touchCurrentX.value = touch.clientX
      // 仅在屏幕左边缘或侧边栏已打开时启动滑动判定
      const isEdgeStart = touch.clientX < edgeThreshold
      if (isEdgeStart || isMobileSidebarOpen.value) {
        isSwiping.value = true
      }
    }

    const handleTouchMove = (event) => {
      if (!isSwiping.value) return
      const touch = event.touches[0]
      touchCurrentX.value = touch.clientX
      // 判定为水平滑动而非垂直滚动：水平位移大于垂直位移
      const deltaX = Math.abs(touch.clientX - touchStartX.value)
      const deltaY = Math.abs(touch.clientY - touchStartY.value)
      if (deltaY > deltaX) {
        isSwiping.value = false
      }
    }

    const handleTouchEnd = () => {
      if (!isSwiping.value) return
      const deltaX = touchCurrentX.value - touchStartX.value
      // 从左边缘右滑：打开侧边栏
      if (touchStartX.value < edgeThreshold && deltaX > swipeThreshold) {
        isMobileSidebarOpen.value = true
      }
      // 侧边栏打开时左滑：关闭侧边栏
      else if (isMobileSidebarOpen.value && deltaX < -swipeThreshold) {
        isMobileSidebarOpen.value = false
      }
      isSwiping.value = false
    }

    const goToProfile = () => {
      closeAllDropdowns()
      // TODO: 导航到个人资料页面
    }

    const goToSettings = () => {
      closeAllDropdowns()
      store.commit('setCurrentPage', 'config')
    }

    // 点击外部关闭下拉菜单
    const handleClickOutside = (event) => {
      const dropdowns = document.querySelectorAll('.language-dropdown, .theme-dropdown, .user-menu')
      let clickedInside = false
      dropdowns.forEach(dropdown => {
        if (dropdown.contains(event.target)) {
          clickedInside = true
        }
      })
      if (!clickedInside) {
        closeAllDropdowns()
      }
    }

    // 检测移动端
    const checkMobile = () => {
      isMobile.value = window.innerWidth <= 768
      if (!isMobile.value) {
        isMobileSidebarOpen.value = false
      }
    }

    // 生命周期
    onMounted(() => {
      // 同步 i18n locale 与 store 中保存的语言偏好（避免刷新后语言回退到默认 'zh'）
      const savedLanguage = store.state.language
      if (savedLanguage && savedLanguage !== locale.value) {
        locale.value = savedLanguage
      }
      document.addEventListener('click', handleClickOutside)
      window.addEventListener('resize', checkMobile)
      // 触摸手势：仅在移动端启用
      document.addEventListener('touchstart', handleTouchStart, { passive: true })
      document.addEventListener('touchmove', handleTouchMove, { passive: true })
      document.addEventListener('touchend', handleTouchEnd, { passive: true })
      checkMobile()
    })

    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside)
      window.removeEventListener('resize', checkMobile)
      document.removeEventListener('touchstart', handleTouchStart)
      document.removeEventListener('touchmove', handleTouchMove)
      document.removeEventListener('touchend', handleTouchEnd)
    })

    return {
      isLoggedIn,
      currentPage,
      isSidebarCollapsed,
      isDarkTheme,
      currentTheme,
      themeList,
      currentLanguage,
      username,
      userInitials,
      currentComponent,
      pageTitle,
      navItems,
      availableLanguages,
      isSearchExpanded,
      searchQuery,
      searchInput,
      isLanguageDropdownOpen,
      isThemeDropdownOpen,
      isUserMenuOpen,
      isMobileSidebarOpen,
      isMobile,
      toggleSidebar,
      handleNavClick,
      handleLogout,
      toggleTheme,
      toggleThemeDropdown,
      changeTheme,
      toggleSearch,
      closeSearch,
      toggleLanguageDropdown,
      changeLanguage,
      toggleUserMenu,
      openMobileSidebar,
      closeMobileSidebar,
      handleTouchStart,
      handleTouchMove,
      handleTouchEnd,
      goToProfile,
      goToSettings
    }
  }
}
</script>

<style scoped>
/* 应用容器 - 液态玻璃基础 */
.app-wrapper {
  min-height: 100vh;
  display: flex;
  background: var(--ios-bg-base);
  position: relative;
  transition: var(--ios-theme-transition);
}

/* 侧边栏 - 液态玻璃效果 */
.app-sidebar {
  width: var(--ios-sidebar-width);
  height: 100vh;
  height: 100dvh;
  background: var(--ios-sidebar-bg);
  backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  -webkit-backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  border-right: 0.5px solid var(--ios-sidebar-border);
  box-shadow: inset -0.5px 0 0 0 var(--ios-glass-highlight);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  /* Safe area: 留出状态栏和底部 Home Indicator 空间 */
  padding-top: var(--ios-safe-area-top);
  padding-bottom: var(--ios-safe-area-bottom);
  padding-left: var(--ios-safe-area-left);
  z-index: var(--ios-z-fixed);
  transition: width var(--ios-transition-spring),
              background var(--ios-transition-normal),
              border-color var(--ios-transition-normal),
              transform var(--ios-transition-spring);
  overflow: hidden;
}

.app-sidebar.sidebar-collapsed {
  width: var(--ios-sidebar-collapsed-width);
}

/* iOS 26 品牌区域 */
.sidebar-brand {
  height: 64px;
  padding: 0 var(--ios-space-4);
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
  border-bottom: 0.5px solid var(--ios-separator);
  position: relative;
}

.brand-logo {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon {
  width: 100%;
  height: 100%;
}

.brand-text {
  font-size: var(--ios-text-title3);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
  white-space: nowrap;
  overflow: hidden;
  letter-spacing: var(--ios-tracking-tight);
  transition: opacity var(--ios-transition-fast);
}

.sidebar-toggle-btn {
  position: absolute;
  right: var(--ios-space-3);
  width: 28px;
  height: 28px;
  border-radius: var(--ios-radius-sm);
  border: none;
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--ios-transition-fast);
  opacity: 0;
}

.app-sidebar:hover .sidebar-toggle-btn {
  opacity: 1;
}

.sidebar-toggle-btn:hover {
  background: var(--ios-blue);
  color: white;
}

.toggle-icon {
  width: 18px;
  height: 18px;
  transition: transform var(--ios-transition-spring);
}

.toggle-icon.rotated {
  transform: rotate(180deg);
}

/* iOS 26 导航菜单 */
.sidebar-nav {
  flex: 1;
  padding: var(--ios-space-3);
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-1);
}

.nav-item-wrapper {
  position: relative;
}

.nav-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
  padding: var(--ios-space-3);
  border-radius: var(--ios-radius-lg);
  border: none;
  background: transparent;
  color: var(--ios-label-secondary);
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  cursor: pointer;
  transition: all var(--ios-transition-fast);
  position: relative;
  text-align: left;
}

.nav-item:hover {
  background: var(--ios-fill-quaternary);
  color: var(--ios-label-primary);
}

.nav-item.active {
  background: var(--ios-blue);
  color: white;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

.nav-item.active:hover {
  background: #0066d6;
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.4);
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-svg {
  width: 100%;
  height: 100%;
}

.nav-text {
  white-space: nowrap;
  overflow: hidden;
  transition: opacity var(--duration-fast) var(--ease-out);
}

.nav-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--primary-500);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

/* 侧边栏底部 */
.sidebar-footer {
  padding: var(--spacing-3);
  border-top: 1px solid var(--border-color);
}

.logout-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  border-radius: var(--radius-lg);
  border: none;
  background: transparent;
  color: var(--danger-600);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.logout-btn:hover {
  background: var(--danger-50);
}

.logout-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.logout-text {
  white-space: nowrap;
  overflow: hidden;
}

/* iOS 26 主内容区 */
.app-main {
  flex: 1;
  margin-left: var(--ios-sidebar-width);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left var(--ios-transition-spring);
}

.app-sidebar.sidebar-collapsed ~ .app-main {
  margin-left: var(--ios-sidebar-collapsed-width);
}

/* 顶部导航栏 - 液态玻璃 */
.app-header {
  height: 64px;
  padding: 0 var(--ios-space-6);
  background: var(--ios-glass-bg);
  backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  -webkit-backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  border-bottom: 0.5px solid var(--ios-separator);
  box-shadow: inset 0 -0.5px 0 0 var(--ios-glass-highlight);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: var(--ios-z-sticky);
  transition: var(--ios-theme-transition);
}

.mobile-menu-btn {
  display: none;
  width: 40px;
  height: 40px;
  border-radius: var(--ios-radius-lg);
  border: none;
  background: transparent;
  color: var(--ios-label-secondary);
  cursor: pointer;
  align-items: center;
  justify-content: center;
}

.mobile-menu-btn:hover {
  background: var(--ios-fill-quaternary);
  color: var(--ios-label-primary);
}

.page-title {
  font-size: var(--ios-text-title3);
  font-weight: var(--ios-weight-bold);
  color: var(--ios-label-primary);
  margin: 0;
  letter-spacing: var(--ios-tracking-tight);
}

.header-controls {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
}

/* iOS 26 搜索框 */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-toggle {
  width: 40px;
  height: 40px;
  border-radius: var(--ios-radius-lg);
  border: none;
  background: transparent;
  color: var(--ios-label-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--ios-transition-fast);
}

.search-toggle:hover {
  background: var(--ios-fill-quaternary);
  color: var(--ios-label-primary);
}

.search-input {
  position: absolute;
  right: 0;
  width: 240px;
  height: 40px;
  padding: 0 var(--ios-space-4) 0 var(--ios-space-10);
  border-radius: var(--ios-radius-lg);
  border: none;
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
  font-size: var(--ios-text-subhead);
  outline: none;
  animation: slideInRight var(--ios-duration-fast) var(--ios-ease-out);
}

.search-input:focus {
  background: var(--ios-fill-secondary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

.search-input::placeholder {
  color: var(--ios-label-tertiary);
}

/* iOS 26 控制按钮 */
.control-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--ios-radius-lg);
  border: none;
  background: transparent;
  color: var(--ios-label-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--ios-transition-fast);
}

.control-btn:hover {
  background: var(--ios-fill-quaternary);
  color: var(--ios-label-primary);
}

.control-btn:active {
  transform: scale(0.95);
}

.language-btn {
  width: auto;
  padding: 0 var(--ios-space-3);
  gap: var(--ios-space-2);
}

.language-code {
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-secondary);
}

/* 下拉菜单 - 液态玻璃 */
.language-dropdown,
.theme-dropdown,
.user-menu {
  position: relative;
}

/* 主题选择器菜单 */
.theme-menu {
  min-width: 220px;
  max-height: 380px;
  overflow-y: auto;
}

.theme-item {
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
  padding: var(--ios-space-2) var(--ios-space-3) !important;
}

.theme-item.active {
  background: var(--ios-fill-quaternary);
}

.theme-preview {
  width: 28px;
  height: 28px;
  border-radius: var(--ios-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 0.5px solid var(--ios-glass-border);
  overflow: hidden;
}

.theme-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.theme-name {
  flex: 1;
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-regular);
  color: var(--ios-label-primary);
}

.theme-check {
  width: 16px;
  height: 16px;
  color: var(--ios-blue);
  flex-shrink: 0;
}

.dropdown-header {
  padding: var(--ios-space-2) var(--ios-space-3);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + var(--ios-space-2));
  right: 0;
  min-width: 200px;
  background: var(--ios-glass-bg);
  backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  -webkit-backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-xl);
  box-shadow: var(--ios-shadow-xl), inset 0 1px 0 0 var(--ios-glass-highlight);
  padding: var(--ios-space-2);
  z-index: var(--ios-z-dropdown);
  transition: var(--ios-theme-transition);
}

.dropdown-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
  padding: var(--ios-space-3) var(--ios-space-4);
  border-radius: var(--ios-radius-lg);
  border: none;
  background: transparent;
  color: var(--ios-label-primary);
  font-size: var(--ios-text-subhead);
  cursor: pointer;
  transition: all var(--ios-transition-fast);
}

.dropdown-item:hover {
  background: var(--ios-fill-quaternary);
}

.dropdown-item:active {
  background: var(--ios-fill-tertiary);
}

.dropdown-item.active {
  color: var(--ios-blue);
}

.dropdown-item.danger {
  color: var(--ios-red);
}

.dropdown-item.danger:hover {
  background: rgba(255, 59, 48, 0.1);
}

.lang-flag {
  font-size: var(--font-size-lg);
}

.dropdown-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
}

.user-info {
  display: flex;
  flex-direction: column;
}

.user-fullname {
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.user-role {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.dropdown-divider {
  height: 1px;
  background: var(--border-color);
  margin: var(--spacing-2) 0;
}

.item-icon {
  width: 18px;
  height: 18px;
}

/* iOS 26 用户按钮 */
.user-btn {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
  padding: var(--ios-space-1) var(--ios-space-2) var(--ios-space-1) var(--ios-space-1);
  border-radius: var(--ios-radius-full);
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all var(--ios-transition-fast);
}

.user-btn:hover {
  background: var(--ios-fill-quaternary);
}

.user-btn:active {
  transform: scale(0.98);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--ios-radius-full);
  background: linear-gradient(135deg, var(--ios-blue), var(--ios-purple));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

.user-avatar.large {
  width: 44px;
  height: 44px;
  font-size: var(--ios-text-title3);
}

.user-name {
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-primary);
}

.dropdown-icon {
  width: 16px;
  height: 16px;
  color: var(--ios-label-tertiary);
  transition: transform var(--ios-transition-fast);
}

.dropdown-icon.rotated {
  transform: rotate(180deg);
}

/* 页面内容区 */
.page-content {
  flex: 1;
  padding: var(--ios-space-6);
  overflow-y: auto;
  position: relative;
  z-index: 1;
}

/* 移动端遮罩层 - 毛玻璃 */
.mobile-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: calc(var(--ios-z-fixed) - 1);
  animation: fadeIn var(--ios-duration-fast) var(--ios-ease-out);
}

/* 页面切换动画 */
.page-enter-active,
.page-leave-active {
  transition: all var(--ios-transition-normal);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 下拉菜单动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all var(--ios-transition-fast);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.96);
}

/* iOS 26 响应式设计 */
@media (max-width: 1024px) {
  .app-sidebar {
    width: var(--ios-sidebar-collapsed-width);
  }

  .app-sidebar .brand-text,
  .app-sidebar .nav-text,
  .app-sidebar .logout-text,
  .app-sidebar .sidebar-toggle-btn {
    display: none;
  }

  .app-main {
    margin-left: var(--ios-sidebar-collapsed-width);
  }
}

@media (max-width: 768px) {
  .app-sidebar {
    width: 280px;
    transform: translateX(-100%);
    transition: transform var(--ios-transition-spring);
  }

  .app-sidebar.sidebar-mobile-open {
    transform: translateX(0);
  }

  .app-sidebar .brand-text,
  .app-sidebar .nav-text,
  .app-sidebar .logout-text {
    display: block;
  }

  .app-main {
    margin-left: 0;
  }

  .mobile-overlay {
    display: block;
  }

  .mobile-menu-btn {
    display: flex;
  }

  /* 头部：保留标题，隐藏次要控件 */
  .page-title {
    font-size: var(--ios-text-headline);
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* 搜索框：保留图标按钮，移除展开式输入（移动端体验不佳） */
  .search-box {
    display: none;
  }

  /* 用户名在移动端隐藏（仅显示头像），节省横向空间 */
  .user-name {
    display: none;
  }

  .dropdown-icon {
    display: none;
  }

  .page-content {
    padding: var(--ios-space-4);
    /* 底部留出 Home Indicator 空间 */
    padding-bottom: calc(var(--ios-space-4) + var(--ios-safe-area-bottom));
  }
}

@media (max-width: 480px) {
  .app-header {
    padding: 0 var(--ios-space-3);
    /* 适配顶部状态栏 */
    padding-top: 0;
    height: 56px;
  }

  /* 语言按钮只显示图标，不显示语言代码 */
  .language-code {
    display: none;
  }

  .language-btn {
    width: 40px;
    padding: 0;
    justify-content: center;
  }

  /* 移动端菜单按钮和控件按钮：增大触摸目标 */
  .mobile-menu-btn,
  .control-btn {
    width: 44px;
    height: 44px;
  }

  .page-content {
    padding: var(--ios-space-3);
    padding-bottom: calc(var(--ios-space-3) + var(--ios-safe-area-bottom));
  }
}

/* 极小屏幕：进一步紧凑头部 */
@media (max-width: 360px) {
  .app-header {
    gap: var(--ios-space-1);
  }

  .header-controls {
    gap: var(--ios-space-1);
  }
}

/* 动画关键帧 */
@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* 滚动条样式 */
.sidebar-nav::-webkit-scrollbar {
  width: 4px;
}

.sidebar-nav::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-nav::-webkit-scrollbar-thumb {
  background: var(--ios-fill-tertiary);
  border-radius: var(--ios-radius-full);
}

.page-content::-webkit-scrollbar {
  width: 8px;
}

.page-content::-webkit-scrollbar-track {
  background: transparent;
}

.page-content::-webkit-scrollbar-thumb {
  background: var(--ios-fill-tertiary);
  border-radius: var(--ios-radius-full);
}

.page-content::-webkit-scrollbar-thumb:hover {
  background: var(--ios-fill-secondary);
}

/* GPU加速 - 玻璃态元素性能优化 */
.app-sidebar,
.app-header,
.dropdown-menu {
  transform: translateZ(0);
  will-change: transform;
}

/* Reduced Motion - 禁用背景光斑动画 */
@media (prefers-reduced-motion: reduce) {
  .ios-bg-orb {
    animation: none !important;
  }
}
</style>
