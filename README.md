# Test

具体实现使用python flask+h5页面来进行展示 

app.py  项目后端代码
index.html 项目前端展示界面代码
Login.html 项目前端登录界面代码
自动化脚本.txt  底层linux执行自动化脚本初始化网络环境 

本实验基于ssh+docker 来实现的 后端服务代码会先使用ssh来连接虚拟机 然后执行 ansible命令 获取返回结果
然后通过对结果的过滤 然后把数据渲染到前端页面
