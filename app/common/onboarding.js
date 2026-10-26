// A device preference, independent of account data and backend availability.
export const ONBOARDING_STORAGE_KEY = 'zhiyou.onboarding.v1.completed'
export const ONBOARDING_ROUTE = 'pages/onboarding/onboarding'

export function appEntry(storage, loginProvider) {
  return storage.getStorageSync('token') && storage.getStorageSync('login_provider') === loginProvider
    ? '/pages/tabs/tabs?tab=tour'
    : '/pages/auth/auth'
}
