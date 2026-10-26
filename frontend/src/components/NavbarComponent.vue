<script lang="ts" setup>import LanguageSwitch from '@/components/LanguageSwitch.vue'
import { t } from '@/i18n'

import { Fold, Expand, ArrowDown } from '@/icons'
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { isCollapse } from '@/utils/navbar'
import BreadCrumb from '@/components/BreadCrumb.vue'
import { getUserInfoRequest, type UserInfo } from '@/api/user'
import { useTokenStore } from '@/stores/userToken'
import { ElMessage } from 'element-plus'
import { AxiosError } from 'axios'

const router = useRouter()
const tokenStore = useTokenStore()
const userInfoItem = ref({} as UserInfo)

const roleLabel = computed(() => {
  const role = tokenStore.userInfo.role
  return role === 'admin' ? t("景区管理员") : role === 'guide' ? t("数字导游") : t("运营成员")
})

const displayName = computed(() => userInfoItem.value.username || tokenStore.userInfo.username || t("运营用户"))

const handleLogout = () => {
  tokenStore.logout()
  router.push('/login')
}

onMounted(async () => {
  try {
    const { data } = await getUserInfoRequest()
    if (data.code === 0) {
      userInfoItem.value = data.data
    } else {
      ElMessage.error(t("获取用户信息失败: ") + data.message)
    }
  } catch (error: unknown) {
    if (error instanceof AxiosError) {
      ElMessage.error(t("获取用户信息失败: ") + error.message)
    } else {
      ElMessage.error(t("未知错误：") + error)
    }
  }
})
</script>

<template>
  <el-header class="topbar">
    <button class="collapse-trigger" type="button" :aria-label='$t("切换侧边栏")' @click="isCollapse = !isCollapse">
      <el-icon class="collapse-icon"><Expand :class="{'icon-current':isCollapse}" /><Fold :class="{'icon-current':!isCollapse}" /></el-icon>
    </button>

    <BreadCrumb class="breadcrumb" />

    <div class="topbar-actions">
        <LanguageSwitch />

      <el-dropdown trigger="click" placement="bottom-end">
        <button class="user-trigger" type="button">
          <el-avatar :size="34" :src="userInfoItem.avatar" class="user-avatar">{{ displayName.slice(0, 1) }}</el-avatar>
          <span class="user-meta">
            <strong>{{ displayName }}</strong>
            <small>{{ $t(roleLabel) }}</small>
          </span>
          <el-icon class="arrow"><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu class="user-dropdown">
            <el-dropdown-item disabled>{{ $t(roleLabel) }}</el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">{{ $t("退出登录") }}</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<style lang="scss" scoped>
.topbar {
  display: flex;
  align-items: center;
  height: 68px;
  padding: 0 26px;
  border-bottom: 1px solid var(--line-soft);
  background: var(--glass);
  box-shadow: var(--glass-shadow);
  backdrop-filter: none;
}

.collapse-trigger,
.user-trigger {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.collapse-trigger {
  display: inline-grid;
  width: 34px;
  height: 34px;
  margin-right: 16px;
  place-items: center;
  border-radius: 8px;
  color: var(--ink-700);
  background: transparent;
  transition: background-color 0.16s ease, color 0.16s ease;

  &:hover {
    color: var(--brand-700);
    background: var(--brand-50);
  }

  .el-icon {
    font-size: 18px;
  }
}

.breadcrumb :deep(.el-breadcrumb__inner),
.breadcrumb :deep(.el-breadcrumb__inner a) {
  color: var(--ink-500);
  font-size: 18px;
  font-weight: 600;
}

.breadcrumb :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--ink-900);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-left: auto;
}

.system-health {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--ink-500);
  font-size: 18px;

  .el-icon {
    color: var(--brand-600);
  }

  b {
    padding: 2px 6px;
    border-radius: 4px;
    color: var(--success);
    background: var(--glass);
    font-size: 18px;
    font-weight: 700;
  }
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 3px 0 3px 8px;
  color: var(--ink-900);
  background: transparent;
}

.user-avatar {
  border: 2px solid var(--glass-line);
  color: var(--brand-700);
  background: var(--brand-100);
  font-size: 18px;
  font-weight: 800;
}

.user-meta {
  display: grid;
  gap: 2px;
  min-width: 72px;
  text-align: left;

  strong {
    max-width: 118px;
    overflow: hidden;
    color: var(--ink-900);
    font-size: 18px;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  small {
    color: var(--ink-500);
    font-size: 18px;
  }
}

.arrow {
  color: var(--ink-400);
  font-size: 18px;
}

.topbar {
  height: 64px;
  padding: 0 24px;
  border-bottom-color: var(--glass-line);
  background: var(--glass);
  box-shadow: var(--glass-shadow);
}
.collapse-trigger:hover { color: var(--champagne-text); background: var(--glass); }
.system-health .el-icon { color: var(--champagne-text); }
.system-health b { color: var(--champagne-text); background: var(--glass); }
.user-avatar { border-color: var(--glass-line); color: var(--champagne-text); background: var(--glass); }

/* Clean exhibition topbar */
.topbar {
  height: 68px;
  padding: 0 28px;
  border-bottom-color: var(--glass-line);
  background: var(--glass);
  box-shadow: none;
  backdrop-filter: none;
}
.collapse-trigger:hover { color: var(--champagne-text); background: var(--glass); }
.system-health .el-icon { color: var(--champagne-text); }
.system-health b { color: var(--champagne-text); background: var(--glass); }
.user-avatar { border-color: var(--glass-line); color: var(--champagne-text); background: var(--glass); }
</style>
