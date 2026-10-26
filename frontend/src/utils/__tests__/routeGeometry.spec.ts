import { describe, it, expect } from 'vitest'
import { roadPoints, roadPaths, routeLegs } from '../routeGeometry'
import type { RouteOverviewData, WalkingLeg } from '@/api/tourExperience'
const leg=(geometry?:number[][]):WalkingLeg=>({from_id:1,to_id:2,from_name:'A',to_name:'B',meters:200,minutes:3,basis:'osm_pedestrian_network',geometry})
describe('actual pedestrian geometry',()=>{
 it('does not draw a connector from stop coordinates when road geometry is missing',()=>{
  const route={stops:[{latitude:39.99,longitude:116.26},{latitude:40,longitude:116.27}],legs:[leg()]} as RouteOverviewData
  expect(roadPaths(route)).toEqual([])
 })
 it('preserves road bends and keeps disconnected sections separate',()=>{
  const first=leg([[39.99,116.26],[39.9901,116.26],[39.9901,116.261]])
  const exit=leg([[39.992,116.27],[39.993,116.27]])
  const route={stops:[],legs:[first,leg()],exit_leg:exit} as unknown as RouteOverviewData
  expect(roadPaths(route).map(path=>path.length)).toEqual([3,2])
  expect(routeLegs(route)).toHaveLength(3)
 })
 it('rejects explicitly unavailable or invalid geographic geometry',()=>{
  expect(roadPoints({...leg([[39,116],[40,117]]),available:false})).toEqual([])
  expect(roadPoints(leg([[91,116],[40,117]]))).toEqual([])
  expect(roadPoints(leg([[39,Number.NaN],[40,117]]))).toEqual([])
 })
 it('includes entrance and exit approaches in the displayed route',()=>{
  const entry=leg([[39.99,116.26],[39.991,116.26]]),middle=leg([[39.991,116.26],[39.992,116.26]]),exit=leg([[39.992,116.26],[39.993,116.26]])
  expect(routeLegs({stops:[],entry_leg:entry,legs:[middle],exit_leg:exit} as unknown as RouteOverviewData)).toEqual([entry,middle,exit])
 })
})
