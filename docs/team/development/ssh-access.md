# Перенос допуска SSH для legioner

Процедуру выполняет администратор на Ubuntu 24.04 при первом включении политики. Она сохраняет общий логин и персональные ключи команды. Последующие выдача и отзыв описаны в [руководстве по VPS](vps.md#управление-доступом).

### Подготовить проверенный список

Оставьте открытым отдельное административное соединение до проверки нового входа. В root-сессии запустите вложенную оболочку командой `flock /run/lock/mslegion-ssh-keys.lock bash`. Следующие команды выполняйте в этой оболочке. Они рассчитаны на штатный сервис Ubuntu `ssh` и глобальный `Include /etc/ssh/sshd_config.d/*.conf` в начале основного файла. При нестандартном запуске сначала установите, какую конфигурацию читает работающий демон.

```bash
set -eu
umask 077
work=$(mktemp -d /root/mslegion-ssh.XXXXXXXX)
printf 'Каталог снимка и отката: %s\n' "$work"
keys=/etc/ssh/authorized_keys/legioner
policy=/etc/ssh/sshd_config.d/00-mslegion-legioner.conf
source_policy=/opt/mslegion-staging/current/deploy/staging/sshd-legioner.conf
test -f "$source_policy"
test ! -e "$policy" && test ! -L "$policy" || exit 1
test ! -e "$keys" && test ! -L "$keys" || exit 1
read -r peer _ local_addr local_port <<< "$SSH_CONNECTION"
context="host=$peer,addr=$peer,laddr=$local_addr,lport=$local_port"
sshd -T -C "user=root,$context" > "$work/root.before"
sshd -T -C "user=legioner,$context" > "$work/legioner.before"
```

Используйте адреса реальных подключений для проверок `sshd -T -C`. Если команда подключается из другой сети или действуют правила `Match Host`, `Address`, `LocalAddress` или `LocalPort`, проверьте также соответствующие им контексты. Убедитесь, что переход сохраняет ранее обязательные факторы входа. При действующем MFA сохраните обязательный второй фактор в политике и проверках ниже. Если указанные целевые файлы уже существуют, изучите установленную политику до продолжения.

Для перехода со старой схемы снимите копию с полномочиями владельца домашнего файла. На новом хосте подготовьте `$work/legioner` непосредственно из согласованных публичных ключей.

```bash
runuser -u legioner -- cat /home/legioner/.ssh/authorized_keys > "$work/legioner"
ssh-keygen -lf "$work/legioner"
```

Сверьте отпечатки с независимо подтверждённым составом пользователей. Проверьте полные строки снимка, включая дубликаты, ограничения команд, адресов, сроков и записи центров сертификации, если они есть. Оставьте только согласованные строки с их исходными ограничениями. Дальше устанавливается именно этот проверенный снимок.

### Установить и проверить политику

```bash
if [ ! -d /etc/ssh/authorized_keys ]; then
    install -d -o root -g root -m 0755 /etc/ssh/authorized_keys
fi
namei -l /etc/ssh/authorized_keys
```

Убедитесь, что каталог списка и каталог конфигурации принадлежат root и ни один компонент пути не допускает замены со стороны `legioner`. Рабочий режим каталога списка — 0755. Сам список доступен этой учётной записи на чтение через её группу.

```bash
install -o root -g legioner -m 0640 "$work/legioner" "$keys"
runuser -u legioner -- test -r "$keys"
runuser -u legioner -- test ! -w "$keys"
runuser -u legioner -- test ! -w /etc/ssh/authorized_keys

verify_policy() {
    sshd -t &&
        sshd -T -C "user=root,$context" > "$work/root.after" &&
        cmp -s "$work/root.before" "$work/root.after" &&
        sshd -T -C "user=legioner,$context" > "$work/legioner.after" &&
        grep -Fxq "authorizedkeysfile $keys" "$work/legioner.after" &&
        grep -Fxq 'authorizedkeyscommand none' "$work/legioner.after" &&
        grep -Fxq 'trustedusercakeys none' "$work/legioner.after" &&
        grep -Fxq 'pubkeyauthentication yes' "$work/legioner.after" &&
        grep -Fxq 'authenticationmethods publickey' "$work/legioner.after"
}
install -o root -g root -m 0644 "$source_policy" "$policy"
if ! verify_policy; then
    mv -T -- "$policy" "$work/policy.rejected"
    echo 'Проверка конфигурации не прошла. Перезагрузка SSH отменена.' >&2
    exit 1
fi
```

Проверьте `sshd -T -C` для остальных применимых адресных условий перед `systemctl reload ssh`. В совпавших блоках `Match` для каждой директивы действует первое значение. Для `legioner` должен действовать только проверенный список, а параметры административного входа должны совпасть со снимком. [Справочник OpenSSH для Ubuntu 24.04](https://manpages.ubuntu.com/manpages/noble/man5/sshd_config.5.html#Match)

Выполните `systemctl reload ssh`. Из другого окна откройте **новое** соединение действующим ключом команды. Для настроенного клиентского псевдонима используйте `ssh -S none -o BatchMode=yes -o IdentitiesOnly=yes mslegion id -un`. Ожидается `legioner`. Отдельно проверьте новый административный вход. После успешной проверки завершите вложенную оболочку командой `exit`.

**Откат первого включения.** Если reload или проверочный вход завершились ошибкой, сохранённая административная сессия позволяет исправить конфигурацию. Для возврата к исходной политике сначала сверьте прежний источник с проверенным снимком. Переместите `/etc/ssh/sshd_config.d/00-mslegion-legioner.conf` в каталог снимка, напечатанный при подготовке, затем выполните `sshd -t && systemctl reload ssh` и проверьте новый вход. Если после перехода уже отзывались ключи или доверие к домашнему списку утрачено, восстановите доступ через актуальный список под контролем root.
