from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QAbstractAnimation, QTimer
import time,threading

INFINITY=1000
LEVEL_NUMS=20 #楼层数

# 电梯状态 elev_state
RUNNING_UP=0 #上行
RUNNING_DOWN=1 # 下行
STILL = 2 # 静止

# 乘客选择状态
GO_UP=0
GO_DOWN=1
NONE=2

# 时间
DOOR_TIME=1 # 开关门时间
DELAY_TIME=0.5 # 启动、静止切换延迟时间
RUN_TIME=1 # 运行时通过一层时间
WAIT_TIME=5 # 等待接客时间
WAIT_TIME_2=6
WAIT_TIME_3=7

# 警报状态 warn_state
USABLE=1 # 电梯可用
DISABLE=0 # 电梯损坏

# 门的管理
OPEN_DOOR=0 # 开门
CLOSE_DOOR=1 # 关门
DOOR_OPENED=1 # 门在开着
DOOR_CLOSED=0 # 门在关着


# 动画状态
READY_START=0 # 就绪运行
READY_STOP=1 # 就绪停止
NOPE=2 # 空状态


class Controller(object):
    def __init__(self,n,UI):
        # 计时器1s一更新
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateState)
        self.timer.start(1000)

        # 电梯数量
        self.elevNum=n

        # 控制器控制的UI界面
        self._elev=UI

        # 标识电梯内部开关门按钮的状态
        self.door_ctrl_state=[]
        for i in range(5):
            self.door_ctrl_state.append(NOPE)


        # 每层楼的调度状况
        # 初始默认没有调度
        self.level_cmd=[]
        for i in range(LEVEL_NUMS):
            self.level_cmd.append(NONE)

        # 电梯门状态
        self.doorsState = []
        for i in range(5):
            self.doorsState.append(DOOR_CLOSED)

        # 每个电梯的运行状态
        self.elev_state=[]
        for i in range(self.elevNum):
            self.elev_state.append(STILL)

        # 每个电梯的动画状态
        self.elev_anim_state=[]
        for i in range(self.elevNum):
            self.elev_anim_state.append(NOPE)

        # 每个电梯的警报状态
        self.warn_state=[]
        for i in range(self.elevNum):
            self.warn_state.append(USABLE)

        # 每个电梯当前楼层
        self.cur_level=[]
        for i in range(self.elevNum):
            self.cur_level.append(0)

        # 每个电梯顺行列表
        self.com_list=[]
        for i in range(self.elevNum):
            self.com_list.append([])

        # 每个电梯逆行列表
        self.com_reverse_list=[]
        for i in range(self.elevNum):
            self.com_reverse_list.append([])

    # region 计算接客时间
    # elev->电梯编号， whichFloor->发出命令楼层, choice-> 上行/下行命令
    def _calTime(self, elev, whichFloor):
        t=INFINITY
        # 若电梯静止
        if self.elev_state[elev]==STILL:
            t=abs(self.cur_level[elev]-whichFloor)*RUN_TIME
        else:
            # 若顺行方向
            if (whichFloor<self.cur_level[elev] and self.elev_state[elev]==RUNNING_DOWN) or (whichFloor>self.cur_level[elev] and self.elev_state[elev]==RUNNING_UP):
                c=0
                for e in self.com_list[elev]:
                    if e>whichFloor:
                        c+=1
                    else:
                        break
                t=abs(self.cur_level[elev]-whichFloor)*RUN_TIME
            # 若不顺行
            else:
                t+=abs(self.cur_level[elev]-1)*RUN_TIME+(DELAY_TIME*2+DOOR_TIME*2+WAIT_TIME*1)*len(self.com_list[elev])
                c = 0
                for e in self.com_reverse_list[elev]:
                    if e > whichFloor:
                        c += 1
                    else:
                        break
                t+=abs(1-whichFloor)*RUN_TIME+(DELAY_TIME*2+DOOR_TIME*2+WAIT_TIME*1)*c+DELAY_TIME*1
        return t
    # endregion

    #  region 外部控制调度,选择最短接客时间电梯作为目标电梯
    # whichFloor->发出命令楼层，choice->上行/下行命令
    def externDis(self,whichFloor,choice):
        pick_time = [INFINITY,INFINITY,INFINITY,INFINITY,INFINITY] # 每部电梯去到时间
        ableElev=[] # 可用电梯列表
        for i in range(self.elevNum):
            if self.warn_state[i]==USABLE:
                ableElev.append(i)
        print("可用的电梯列表：",ableElev)

        # 若该层此前没有任务则进行调度
        if self.level_cmd[whichFloor]==NONE:
            # 选择最佳调度电梯
            for ELEV in ableElev:
                #可运行的电梯
                elev_time=self._calTime(ELEV,whichFloor)
                pick_time[ELEV]=elev_time
            # for debug
            print("最短的时间列表：{}".format(pick_time))
            BESTELEV=pick_time.index(min(pick_time))
            print("选择的电梯是：{}".format(BESTELEV))

            # 加入该电梯命令队列
            if self.com_list[BESTELEV]:
                cur_level=self.cur_level[BESTELEV] # 该电梯当前楼层
                elev_state=self.elev_state[BESTELEV] # 该电梯运行状态
                # 不顺路
                if cur_level<=whichFloor and elev_state==RUNNING_DOWN or cur_level>=whichFloor and elev_state==RUNNING_UP:
                    self.com_reverse_list[BESTELEV].append(whichFloor)
                    self.com_reverse_list[BESTELEV].sort(reverse=bool(1 - self.elev_state[BESTELEV]))
            else:
                self.com_list[BESTELEV].append(whichFloor)
                self.com_list[BESTELEV].sort(reverse=bool(self.elev_state[BESTELEV]))
    # endregion

    # region 内部控制调度，将按下的楼层加入命令队列
    # elev->按下楼层的电梯编号，targetFloor->按下的楼层
    def internDis(self,elev,targetFloor):
        curLevel=self.cur_level[elev] # 电梯当前位置
        print("电梯当前位置{},目的地{}".format(curLevel,targetFloor))

        # 目标楼层更高
        if targetFloor>curLevel:
            # 此电梯在静止
            if self.elev_state[elev]==STILL:
                self.com_list[elev].append(targetFloor)
                self.com_list[elev].sort()
            else:
                if self.elev_state[elev]==RUNNING_UP:
                    self.com_list[elev].append(targetFloor)
                    self.com_list[elev].sort()
                    print("加入后电梯{}的指令队列为：".format(elev, self.com_list[elev]))
                else:
                    self.com_reverse_list[elev].append(targetFloor)
                    self.com_reverse_list[elev].sort()
                    print("加入后电梯{}的反向指令队列为：".format(elev, self.com_reverse_list[elev]))

        # 目标楼层更低
        elif targetFloor<curLevel:
            # 此电梯在静止
            if self.elev_state[elev]==STILL:
                self.com_list[elev].append(targetFloor)
                self.com_list[elev].sort(reverse=True)
            else:
                if self.elev_state[elev]==RUNNING_DOWN:
                    self.com_list[elev].append(targetFloor)
                    self.com_list[elev].sort(reverse=True)
                    print("加入后电梯的指令队列为：",self.com_list[elev])
                else:
                    self.com_reverse_list[elev].append(targetFloor)
                    self.com_reverse_list[elev].sort(reverse=True)
                    print("加入后电梯的反向指令队列为：",self.com_reverse_list[elev])

        # 就在目标楼层
        else:
            if self.elev_state[elev]==STILL: # 电梯静止==>开门，回复按钮状态
                self.doorsCtrl(elev,OPEN_DOOR)
                # 模拟电梯内部楼层按钮复原
                self._elev.inLevelButtons[elev][targetFloor].setEnabled(True)
                self._elev.inLevelButtons[elev][targetFloor].setStyleSheet("font: 10pt \"AcadEref\";\n"
                                        "background-color: rgb(226, 226, 226);border-radius: 15px;border:0.5px solid #000000;")
            else:
                self.com_reverse_list[elev].append(targetFloor)
    # endregion


    # 门控制函数
    def doorsCtrl(self,elev,cmd):
        # 静止状态可用的电梯才能控制门
        if self.elev_state[elev]==STILL:
            # 开门命令
            if cmd==OPEN_DOOR:
                if self.doorsState[elev]==DOOR_CLOSED:
                    self.warn_state[elev]=DISABLE # 此电梯禁用
                    self.door_ctrl_state[elev]=OPEN_DOOR # 标识此时按下了开门
                    # 开门
                    self.doorsState[elev] = DOOR_OPENED
                    self.openDoorAnim(elev)
            else:
                if self.doorsState[elev] == DOOR_OPENED:
                    self.warn_state[elev] = USABLE  # 此电梯启用
                    # 关门
                    self.doorsState[elev] = DOOR_CLOSED
                    self.closeDoorAnim(elev)


    def openDoorAnim(self,elev):
        print("准备播放电梯{}的开门动画".format(elev))
        self._elev.doorAnims[2 * elev].setDirection(QAbstractAnimation.Forward)  # 正向设定动画
        self._elev.doorAnims[2 * elev + 1].setDirection(QAbstractAnimation.Forward)
        self._elev.doorAnims[2 * elev].start()  # 开始播放
        self._elev.doorAnims[2 * elev + 1].start()

    def closeDoorAnim(self,elev):
        print("准备播放电梯{}的关门动画。。。。".format(elev))
        self._elev.doorAnims[2 * elev].setDirection(QAbstractAnimation.Backward)  # 正向设定动画
        self._elev.doorAnims[2 * elev + 1].setDirection(QAbstractAnimation.Backward)
        self._elev.doorAnims[2 * elev].start()  # 开始播放
        self._elev.doorAnims[2 * elev + 1].start()

    # 报警器控制函数
    # 找到点击报警按钮的电梯，若此电梯此时在飞STILL状态，忽略
    # 若此电梯此时STILL，将其所有按钮禁用
    def warnsCtrl(self,elev):
        if self.elev_state[elev]==STILL and self.warn_state[elev]==USABLE:
            self.warn_state[elev]=DISABLE
            self._elev.warnButtons[elev].setStyleSheet("border-image:url(resources/warn/a_warn.png)")
            self.MessBox = QtWidgets.QMessageBox.information(self._elev, "WARN", "电梯{}已损坏!".format(elev+1))
            print("电梯{}的报警器被点击，禁用！".format(elev))

            # 内部电梯按钮禁用
            for levelButton in self._elev.inLevelButtons[elev]:
                levelButton.setEnabled(False)
            self._elev.openButtons[elev].setEnabled(False) # 内部开关门按钮禁用
            self._elev.closeButtons[elev].setEnabled(False)
            self._elev.warnButtons[elev].setEnabled(False) # 内部报警按钮禁用
            self.door_ctrl_state[elev]=NOPE # 电梯自动应答关闭


    # 更新电梯状态
    def updateState(self):
        for elev in range(self.elevNum):
            # region 控制电梯门按钮打开后自动关闭
            if self.elev_anim_state[elev]==WAIT_TIME_3:
                self.warn_state[elev] = USABLE  # 此电梯启用
                self.closeDoorAnim(elev)  # 关门
                self.doorsState[elev] = DOOR_CLOSED

                self.door_ctrl_state[elev] = NOPE
                self.elev_anim_state[elev]=NOPE
                print("准备自动关门")
                continue

            if self.elev_anim_state[elev]==WAIT_TIME_2:
                self.elev_anim_state[elev]=WAIT_TIME_3
                print("开门后第二次等待")
                continue

            # 控制开关门动画自动切换
            if self.door_ctrl_state[elev] ==OPEN_DOOR:
                self.elev_anim_state[elev] = WAIT_TIME_2
                print("开门后第一次等待")
                continue
            # endregion


            # 不可用电梯略过
            if self.warn_state[elev] == DISABLE:
                continue

            # region 若电梯可用且命令队列非空
            if self.com_list[elev]:
                # 门在开着，等着关门
                if self.doorsState[elev]==DOOR_OPENED:
                    continue

                # 电梯静止状态
                if self.elev_state[elev]==STILL:
                    print("电梯{}开门接客".format(elev))
                    self.openDoorAnim(elev)

                    # 更新电梯运行状态
                    cmd=self.com_list[elev][0]
                    if cmd>self.cur_level[elev]:
                        self.elev_state[elev]=RUNNING_UP
                        self._elev.screenUPLabels[elev].setStyleSheet("border-image:url(resources/screen/up.png)")
                    elif cmd<self.cur_level[elev]:
                        self.elev_state[elev]=RUNNING_DOWN
                        self._elev.screenDWLabels[elev].setStyleSheet("border-image:url(resources/screen/down.png)")
                    else:
                        self.elev_state[elev]=RUNNING_UP

                    self.elev_anim_state[elev]=READY_START # 静止==>就绪运行
                    print("静止状态转为就绪运行状态，发生了开门，转换状态")

                # 就绪运行状态
                if self.elev_anim_state[elev]==READY_START:
                    self.closeDoorAnim(elev)
                    self.elev_anim_state[elev]=NOPE # 动画置空
                    print("就绪运行状态，发生了关门")

                # 换客时间
                if self.elev_anim_state[elev]==READY_STOP:
                    self.elev_anim_state[elev]=WAIT_TIME
                    continue

                # 就绪停止状态
                if self.elev_anim_state[elev]==WAIT_TIME:
                    self.com_list[elev].pop(0)  # 结束当前命令
                    self.level_cmd[elev]=NONE
                    self.closeDoorAnim(elev)
                    self.elev_anim_state[elev]=NOPE # 动画置空
                    self.elev_state[elev]=STILL # 就绪停止==>静止
                    self._elev.screenUPLabels[elev].setStyleSheet("border-image:url(resources/screen/up_2.png)")
                    self._elev.screenDWLabels[elev].setStyleSheet("border-image:url(resources/screen/down_2.png)")
                    print("就绪停止转为静止状态，发生了关门")

                elif self.warn_state[elev]==USABLE:
                    cmd=self.com_list[elev][0] # 下一个目标楼层
                    if cmd>self.cur_level[elev] :
                        self.elev_state[elev]=RUNNING_UP
                        self.cur_level[elev]+=1
                        print("电梯{}显示楼层{},目标指令是{}".format(elev, self.cur_level[elev]+1,cmd))
                        #  电梯显示屏幕数字变化
                        self._elev.screenLevelLabels[elev].setProperty("value", self.cur_level[elev]+1)
                    elif cmd<self.cur_level[elev]:
                        self.elev_state[elev] = RUNNING_DOWN
                        self.cur_level[elev]-=1
                        print("电梯{}显示楼层{},目标指令是{}".format(elev,self.cur_level[elev]+1,cmd))
                        #  电梯显示屏幕数字变化
                        self._elev.screenLevelLabels[elev].setProperty("value", self.cur_level[elev]+1)
                    else:
                        #  内部电梯按钮复原
                        self._elev.inLevelButtons[elev][cmd].setEnabled(True)
                        self._elev.inLevelButtons[elev][cmd].setStyleSheet("font: 10pt \"AcadEref\";\n"
                                        "background-color: rgb(226, 226, 226);border-radius: 15px;border:0.5px solid #000000;")
                        self.openDoorAnim(elev)
                        self._elev.levelCmdButtons[2*cmd].setStyleSheet("border-image:url(resources/btn/up_btn_normal.png)")
                        self._elev.levelCmdButtons[2*cmd+1].setStyleSheet("border-image:url(resources/btn/down_btn_normal.png)")

                        self.elev_anim_state[elev]=READY_STOP  # 运行==> 就绪停止
                        print("已到达目标楼层，转为就绪停止状态")
            # endregion

            # 若反向命令队列非空
            elif self.com_reverse_list[elev]:
                self.com_list[elev]=self.com_reverse_list[elev].copy()
                self.com_reverse_list[elev].clear()

if __name__=="__main__":
    elev=Controller(5)
    elev.externDis(3,GO_UP)












