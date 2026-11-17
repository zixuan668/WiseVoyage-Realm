import { backendAssetUrl } from './backendAssetUrl'

/** Resolve legacy local file URLs through the same backend proxy as the admin API. */
export function adminAssetUrl(value: string | null | undefined): string {
  return backendAssetUrl(value)
}
