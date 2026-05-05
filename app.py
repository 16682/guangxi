import os
import subprocess
import threading
from flask import Flask, request, jsonify
import yaml

app = Flask(__name__)
lock = threading.Lock()

@app.route('/api/sign', methods=['POST'])
def sign_api():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    school = data.get('school')
    photo_url = data.get('photo', '')
    
    # 🌟 直接接收前端传来的经纬度 (不再自己去查地图)
    lon = data.get('lon')
    lat = data.get('lat')

    # 校验：确保前端必须把坐标传过来
    if not all([username, password, school, lon, lat]):
        return jsonify({'code': 400, 'msg': '参数不全，请确保经纬度已填写'})

    with lock:
        try:
            # 1. 构造若离需要的 config.yml 格式
            user_config = {
                # --- 🌟 以下是补充的全局通用配置，写死在代码里解决 KeyError 报错 ---
                'apple': "https://apple.ruoli.cc/captcha/validate",
                'locationOffsetRange': 50, # 签到坐标随机偏移范围(单位：米)
                'maxTry': 3,               # 最大尝试次数
                'logDir': "_log/",         # 日志保存地址
                'delay': [5, 10],          # 多用户延迟
                'captcha': {},             # 留空，不配置验证码推送
                'sendMessage': {},         # 留空，不配置消息推送
                
                # --- 以下是前端传入的动态数据 ---
                'users': [
                    {
                        'type': 2,         # 2 为查寝，1 为签到 (按需调整)
                        'schoolName': school,
                        'username': username,
                        'password': password,
                        'signLevel': 1,
                        'title': 0,
                        'checkTitle': 0,
                        'abnormalReason': "", # 补充缺失字段
                        'lon': float(lon),  # 直接写入用户精准经度
                        'lat': float(lat),  # 直接写入用户精准纬度
                        'address': school,
                        'photo': photo_url
                    }
                ]
            }
            # user_config = {
            #     'users': [
            #         {
            #             'type': 2,
            #             'schoolName': school,
            #             'username': username,
            #             'password': password,
            #             'signLevel': 1,
            #             'title': 0,
            #             'checkTitle': 0,
            #             'lon': float(lon),  # 🌟 直接写入用户从百度拾取的精准经度
            #             'lat': float(lat),  # 🌟 直接写入用户从百度拾取的精准纬度
            #             'address': school,
            #             'photo': photo_url
            #         }
            #     ]
            # }
            
            # 2. 写入配置文件
            with open("config.yml", "w", encoding="utf-8") as f:
                yaml.dump(user_config, f, allow_unicode=True, sort_keys=False)
            
            # 3. 执行打卡脚本
            result = subprocess.run(["python", "index.py"], capture_output=True, text=True, cwd=".")
            output = result.stdout + result.stderr

            # 4. 分析执行日志
            if "签到成功" in output or "成功" in output or "success" in output.lower():
                return jsonify({'code': 200, 'msg': '签到成功', 'log': output})
            elif "密码错误" in output or "认证失败" in output:
                return jsonify({'code': 400, 'msg': '账号或密码错误'})
            elif "不需要" in output or "已签到" in output:
                return jsonify({'code': 200, 'msg': '当前不在签到时间或已完成签到'})
            else:
                return jsonify({'code': 400, 'msg': '签到失败，请检查坐标或稍后再试', 'log': output})
                
        except Exception as e:
            return jsonify({'code': 500, 'msg': f"API执行异常: {str(e)}"})

# 增加一个简单的 ping 接口，用于 UptimeRobot 保活唤醒
@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'code': 200, 'msg': 'pong'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
