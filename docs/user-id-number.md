# 用户展示编号（user_no）

## 规则

- 格式：`年月 + 4 位注册顺序`，共 10 位。第一个注册的用户编号为 `2026100001`（2026 年 10 月第 1 位）。
- 年月按北京时间取；每个月第 1 个注册的用户从 `0001` 重新开始。
- 编号会持久化到数据库，账号换昵称、换头像、重新登录都不会变化。
- 数据库内部主键仍然是 `user_info.user_id`（整数），登录 token、关联表外键都不受影响；`user_no` 是新增的唯一展示编号。

## 实现位置

| 位置 | 说明 |
| --- | --- |
| `server/base/modules/user_number.py` | 取号、月份前缀、历史账号补号 |
| `server/base/models/user_model.py` | `UserBaseInfo.user_no` 字段（唯一） |
| `server/base/routers/users.py` | 邮箱注册成功后分配编号 |
| `server/base/utils.py` | 首个管理员创建时分配编号 |
| `server/base/database/init_db.py` | 启动迁移：补列 + 唯一索引 + 历史账号补号 |
| `app/pages/mine/mine.vue` | 个人页优先显示 `user_no` |

## 并发与迁移

- 取号在同一事务内使用 PostgreSQL 咨询锁 `73192842` 串行化，并发注册不会拿到重复编号。
- 服务启动时自动执行迁移，幂等：已有编号的账号保持不动，只给 `user_no IS NULL` 的历史账号按注册顺序补号。
- 历史账号补号统一使用补号当月的年月（当前库里有 4 个 2026 年 7 月注册的老账号，迁移后编号为 `2026100001` ~ `2026100004`）。

## 验证

```powershell
python -m unittest discover -s scripts/tests -p "test_user_number.py" -v
python -m unittest discover -s scripts/tests -p "test_nickname_registration.py" -v
```

接口验证：`GET /api/v1/user/me` 返回

```json
{"user_id": 1, "user_no": "2026100001", "username": "小智", "...": "..."}
```
