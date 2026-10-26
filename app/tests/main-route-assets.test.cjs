const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto')
const root=path.resolve(__dirname,'..'),manifest=JSON.parse(fs.readFileSync(path.join(root,'static/route-covers/manifest.json'),'utf8'))
test('all three recommended covers ship with the exact main resource checksums',()=>{
 assert.equal(manifest.main_commit,'41480aa887d1034d380ebdddcb8c6d5898e5ec5e');assert.equal(Object.keys(manifest.routes).length,3)
 const source=fs.readFileSync(path.join(root,'pages/tour-guide/tour-guide.vue'),'utf8')
 for(const [name,row]of Object.entries(manifest.routes)){const file=fs.readFileSync(path.join(root,row.asset.slice(1)));assert.equal(crypto.createHash('sha256').update(file).digest('hex'),row.sha256);assert.ok(source.includes(name)&&source.includes(row.asset))}
})
