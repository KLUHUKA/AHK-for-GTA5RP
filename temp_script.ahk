
#Persistent
toggle := false

F5::
if (!toggle) {
    toggle := true
    SetTimer, PixelSearchTimer, 100
    Sleep, 100
    SendEvent, {Shift down}
    SendEvent, {w down}
    TrayTip, Скрипт, Скрипт запущен (Shift + W удерживаются), 1
}
return

F7::
if (toggle) {
    SetTimer, PixelSearchTimer, Off
    SendEvent, {Shift up}
    SendEvent, {w up}
    Sleep, 100
    ; На всякий случай отправим еще один отпуск Shift и W
    SendInput, {Shift up}
    SendInput, {w up}
    toggle := false
    TrayTip, Скрипт, Скрипт выключен (Shift + W отпущены), 1
}
return

PixelSearchTimer:
PixelSearch, x, y, 966, 487, 968, 489, 0x7ED321,, Fast RGB
if (!ErrorLevel) {
    SendInput, {e}
}
return
