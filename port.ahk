
; toggle := false

F5::
if (!toggle) {
    toggle := true
    SetTimer, PixelSearchTimer, 100
    Sleep, 100 ; Подождать перед отправкой
    SendEvent, {Shift down}
    SendEvent, {w down}
    TrayTip, Скрипт, Скрипт запущен (Shift + W удерживаются), 1
}
return

F7 + SHIFT + W::
if (toggle) {
    toggle := false
    SetTimer, PixelSearchTimer, Off
    SendEvent, {Shift up}
    SendEvent, {w up}
    TrayTip, Скрипт, Скрипт выключен (Shift + W отпущены), 1
}
return

PixelSearchTimer:
PixelSearch, x, y, 966, 487, 968, 489, 0x7ED321,, Fast RGB
if (!ErrorLevel) {
    SendInput, {e}
}
return
