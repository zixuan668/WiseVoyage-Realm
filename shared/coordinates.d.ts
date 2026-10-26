/** 参数与返回数组顺序均为 [纬度, 经度]。数据库和 GPS 距离计算采用 WGS84。 */
export function wgs84ToGcj02(lat: number, lng: number): [number, number];
export function gcj02ToWgs84(lat: number, lng: number): [number, number];
