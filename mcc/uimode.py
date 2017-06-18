"""Process User Interface and execute commands.

License:

    MCC - Unified CLI Utility for AWS, Azure and GCP Instance Control.
    Copyright (C) 2017  Robert Peteuil

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

URL:       https://github.com/robertpeteuil/multi-cloud-control
Author:    Robert Peteuil

"""
from __future__ import absolute_import, print_function
from builtins import range
from blessed import Terminal
import sys
from mcc.cldcnct import busy_disp_on, busy_disp_off
from time import sleep
from mcc.colors import C_NORM, C_TI, C_GOOD, C_ERR, MAGENTA, C_WARN, C_STAT
from gevent import monkey

monkey.patch_all()
term = Terminal()


def ui_main(fmt_table, node_dict):
    """Create the base UI in command mode."""
    cmd_action = {"quit": False,
                  "run": node_cmd,
                  "stop": node_cmd,
                  "connect": node_cmd,
                  "details": node_cmd,
                  "update": True}
    uiprint("\033[?25l")  # cursor off
    print("{}\n".format(fmt_table))
    sys.stdout.flush()
    # refresh_main values:
    #   None = loop main-cmd, True = refresh-list, False = exit-program
    refresh_main = None
    while refresh_main is None:
        cmd_todo = get_cmd(node_dict)
        if callable(cmd_action[cmd_todo]):
            refresh_main = cmd_action[cmd_todo](cmd_todo, node_dict)
        else:
            refresh_main = cmd_action[cmd_todo]
    if refresh_main:
        disp_clear(len(node_dict) + 2)
    else:
        uiprint("\033[?25h")  # cursor on
    return refresh_main


def get_cmd(node_dict):
    """Get main command selection."""
    key_lu = {"q": ["quit", True], "r": ["run", True],
              "s": ["stop", True], "u": ["update", True],
              "c": ["connect", True], "d": ["details", True]}
    disp_cmd_bar()
    cmd_valid = False
    flush_input()
    with term.cbreak():
        while not cmd_valid:
            val = input_by_key()
            cmd_todo, cmd_valid = key_lu.get(val.lower(), ["invalid", False])
            if not cmd_valid:
                uiprint(" - {0}Invalid Entry{1}".format(C_ERR, C_NORM))
                sleep(0.5)
                disp_cmd_bar()
    return cmd_todo


def node_cmd(cmd_todo, node_dict):
    """Process commands that target specific nodes."""
    sc = {"run": cmd_startstop, "stop": cmd_startstop,
          "connect": cmd_conn, "details": cmd_details}
    inst_num = tar_selection(cmd_todo, len(node_dict))
    refresh_main = None
    if inst_num != 0:
        (tar_valid, tar_mess) = tar_validate(node_dict, inst_num, cmd_todo)
        if tar_valid:
            # get dynamic sub-command for commands
            #   that use the node logic up to this point, but now deviate
            #   like CONNECT and DETAILS
            # line below will call the returned sub-command dynamically
            subcmd = sc[cmd_todo]
            cmd_result = subcmd(node_dict[inst_num], cmd_todo, tar_mess)
            # cmd_result = cmd_startstop(node_dict[inst_num],cmd_todo,tar_mess)
            if cmd_result != "Command Aborted":
                refresh_main = True
                c_result = C_GOOD
            else:
                c_result = C_WARN
            uiprint_suffix(cmd_result, c_result)
            sleep(1)
        else:  # invalid target
            uiprint_suffix(tar_mess, C_ERR)
            sleep(1)
    else:  # 0 - exit command but not program
        uiprint(" - Exit")
        sleep(0.5)
    return refresh_main


def tar_selection(cmdname, inst_max):
    """Determine Node via alternate input method."""
    cmddisp = cmdname.upper()
    cmd_title = ("\r{1}{0} NODE{2} - Enter {3}Node #{2}"
                 " ({4}0 = Exit Command{2}): ".
                 format(cmddisp, C_TI, C_NORM, C_WARN, MAGENTA))
    disp_cmd_title(cmd_title)
    inst_valid = False
    flush_input()
    with term.cbreak():
        while not inst_valid:
            inst_num = input_by_key()
            try:
                inst_num = int(inst_num)
            except ValueError:
                inst_num = 99999
            if inst_num <= inst_max:
                inst_valid = True
            else:
                uiprint_suffix("Invalid Entry", C_ERR)
                sleep(0.5)
                disp_cmd_title(cmd_title)
    return inst_num


def tar_validate(node_dict, inst_num, cmdname):
    """Validate that command can be performed on target node."""
    # cmd: [required-state, action-to-displayed, error-statement]
    req_lu = {"run": ["stopped", "START", "Already Running"],
              "stop": ["running", "STOP", "Already Stopped"],
              "connect": ["running", "CONNECT to", "Not Running"],
              "details": [node_dict[inst_num].state, "DETAILS for", ""]}
    tm = {True: ("{0}{2}{1} Node {3}{4}{1} ({7}{5}{1} on {3}{6}{1})".
                 format(C_STAT[req_lu[cmdname][1]], C_NORM,
                        req_lu[cmdname][1], C_WARN, inst_num,
                        node_dict[inst_num].name,
                        node_dict[inst_num].cloud_disp, C_TI)),
          False: req_lu[cmdname][2]}
    tar_valid = bool(req_lu[cmdname][0] == node_dict[inst_num].state)
    tar_mess = tm[tar_valid]
    # if req_lu[cmdname][0] == node_dict[inst_num].state:
    #     tar_valid = True
    #     tar_mess = ("{0}{2}{1} Node {3}{4}{1} ({7}{5}{1} on {3}{6}{1})".
    #                 format(C_STAT[req_lu[cmdname][1]], C_NORM,
    #                        req_lu[cmdname][1], C_WARN, inst_num,
    #                        node_dict[inst_num].name,
    #                        node_dict[inst_num].cloud_disp, C_TI))
    # else:
    #     tar_valid = False
    #     tar_mess = req_lu[cmdname][2]
    return (tar_valid, tar_mess)


def cmd_startstop(tar_node, cmdname, tar_mess):
    """Confirm command and execute it."""
    cmd_lu = {"run": ["ex_start_node", "wait_until_running", "Success"],
              "stop": ["ex_stop_node", "", "Init"]}
    delay_lu = {"azure": {"stop": 5}}
    endms_lu = {"azure": {"stop": "Initiated"}}
    conf_mess = ("\r{0} - Confirm [y/N]: ".
                 format(tar_mess))
    if input_yn(conf_mess):
        exec_mess = "\rEXECUTING {0}:   ".format(tar_mess)
        disp_erase_ln()
        uiprint(exec_mess)
        busy_obj = busy_disp_on()  # busy indicator ON
        # cmd_one = cmd_lu[cmdname][0]
        cmd_wait = cmd_lu[cmdname][1]
        cmdpre = getattr(tar_node, "driver")
        # maincmd = getattr(cmdpre, cmd_one)
        maincmd = getattr(cmdpre, cmd_lu[cmdname][0])
        response = maincmd(tar_node)  # noqa
        if cmd_wait:
            # cmdpre = getattr(tar_node, "driver")
            seccmd = getattr(cmdpre, cmd_wait)
            response = seccmd([tar_node])  # noqa
        cmd_end = endms_lu.get(tar_node.cloud, {}).get(cmdname, "Successfull")
        cmd_result = "{0} {1}".format(cmdname.title(), cmd_end)
        # cmd_result = "{0} {1}".format(cmdname.title(),
        #                               cmd_lu[cmdname][2])
        # delay on Azure to allow status to change before node-list refresh
        delay = delay_lu.get(tar_node.cloud, {}).get(cmdname, 0)
        sleep(delay)
        busy_disp_off(busy_obj)  # busy indicator OFF
        uiprint("\033[D\033[D")  # remove extra spaces
    else:
        cmd_result = "Command Aborted"
    return cmd_result


def cmd_conn(tar_node, cmd_todo, tar_mess):
    """Connect to node."""
    cmd_result = "Command Aborted"
    return cmd_result


def cmd_details(tar_node, cmd_todo, tar_mess):
    """Display Node details."""
    cmd_result = "Command Aborted"
    return cmd_result


def input_yn(conf_mess):
    """Print Confirmation Message and Get Y/N response from user."""
    disp_erase_ln()
    uiprint(conf_mess)
    with term.cbreak():
        flush_input()
        val = input_by_key()
    return bool(val.lower() == 'y')


def uiprint(toprint):
    """Print text without charrage return."""
    sys.stdout.write(toprint)
    sys.stdout.flush()


def uiprint_suffix(toprint, clr):
    """Print Colored Suffix Message after command."""
    uiprint(" - {1}{0}{2}".format(toprint, clr, C_NORM))


def disp_cmd_title(cmd_title):
    """Display Title and function statement for current command."""
    disp_erase_ln()
    uiprint(cmd_title)


def disp_cmd_bar():
    """Display Command Bar."""
    cmd_bar = ("\rSELECT COMMAND -  {2}(R){1}un   {0}(C){1}onnect   "
               "{3}(S){1}top   {0}(U){1}pdate Info"
               "   {4}(Q){1}uit: ".
               format(C_TI, C_NORM, C_GOOD, C_ERR, MAGENTA))
    # cmd_bar = ("\rSELECT COMMAND -  {2}(R){1}un   {0}(C){1}onnect   "
    #            "{3}(S){1}top   {0}(D){1}etails   {0}(U){1}pdate Info"
    #            "   {4}(Q){1}uit: ".
    #            format(C_TI, C_NORM, C_GOOD, C_ERR, MAGENTA))
    disp_erase_ln()
    uiprint(cmd_bar)


def disp_clear(numlines):
    """Clear previous display info from screen in prep for new data."""
    disp_erase_ln()
    for i in range(numlines, 0, -1):
        uiprint("\033[A")
        disp_erase_ln()


def disp_erase_ln():
    """Erase line above and position cursor on that line."""
    blank_ln = " " * (term.width - 1)
    uiprint("\r{0}".format(blank_ln))


def flush_input():
    """Flush the input buffer on posix and windows."""
    try:
        import sys, termios  # noqa
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except ImportError:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()


def input_by_key():
    """Get user input using inkey to prevent /n printing at end."""
    usr_inp = ''
    input_valid = True
    flush_input()
    with term.cbreak():
        while input_valid:
            uiprint("\033[?25h")  # cursor on
            key_raw = term.inkey()
            if key_raw.name == "KEY_ENTER":
                input_valid = False
                uiprint("\033[?25l")  # cursor off
                break
            if key_raw.name == 'KEY_DELETE':
                usr_inp = usr_inp[:-1]
                uiprint("\033[D \033[D")
            if not key_raw.is_sequence:
                usr_inp += key_raw
                uiprint(key_raw)
    return usr_inp
