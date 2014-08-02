kill -9 `ps -ef|grep fcitx|grep -v grep |awk '{print $2}'`
sleep 1
echo 'start ....'
fcitx -r --enable sogou-qimpanel
sogou-qimpanel
