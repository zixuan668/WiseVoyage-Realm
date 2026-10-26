import type { StationDirections } from '@/api/serviceStation'

/** Road names describe passages, not surveyed landmarks or turn instructions. */
export function namedWalkingPassages(sections: StationDirections['sections'], destination: string) {
  const names: string[] = []
  const generic =
    /^(?:园内步道|未命名(?:道路|步道)?|步道|台阶|人行道|footway|path|steps|unnamed(?:\s+(?:road|path))?)$/i
  for (const section of sections) {
    const name = (section.road_name || '').trim()
    if (!name || generic.test(name) || names.at(-1) === name) continue
    names.push(name)
  }
  // The destination is already shown as the final endpoint.
  if (names.at(-1) === destination.trim()) names.pop()
  return names
}
