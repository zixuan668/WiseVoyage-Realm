import { ref } from 'vue'
import { defineStore } from 'pinia'

interface TokenItem {
  access_token: string
  token_type: string
}

interface UserInfo {
  username: string
  role: 'admin' | 'guide' | 'visitor'  // 管理员 / 导游 / 游客
}

const useTokenStore = defineStore('user-token', {
  state: () => {
    const token = ref({} as TokenItem)
    const userInfo = ref<UserInfo>({ username: '', role: 'visitor' })

    function saveToken(data: TokenItem) {
      token.value = data
    }

    function saveUserInfo(info: UserInfo) {
      userInfo.value = info
    }

    function logout() {
      token.value = {} as TokenItem
      userInfo.value = { username: '', role: 'visitor' }
    }

    return { token, userInfo, saveToken, saveUserInfo, logout }
  },

  persist: {
    paths: ['token', 'userInfo'],
    storage: localStorage
  }
})

export { type TokenItem, type UserInfo, useTokenStore }
