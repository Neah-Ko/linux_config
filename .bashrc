# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
#[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
	# We have color support; assume it's compliant with Ecma-48
	# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
	# a case would tend to support setf rather than setaf.)
	color_prompt=yes
    else
	color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    #alias grep='grep --color=auto'
    #alias fgrep='fgrep --color=auto'
    #alias egrep='egrep --color=auto'
fi

# colored GCC warnings and errors
#export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# some more ls aliases
#alias ll='ls -l'
#alias la='ls -A'
#alias l='ls -CF'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# Dbx
export DATABRICKS_CONFIG_PROFILE="dev"

# ---- Proxy setup -> moved to /etc/environment
# export http_proxy=http://127.0.0.1:9000
# export no_proxy=127.0.0.1,localhost
# export HTTP_PROXY=$http_proxy
# export https_proxy=$http_proxy
# export HTTPS_PROXY=$http_proxy
# export NO_PROXY=$no_proxy
# export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
# export NODE_EXTRA_CA_CERTS=$SSL_CERT_FILE
# export JAVA_OPTS="-Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9000"
# export DONT_PROMPT_WSL_INSTALL=1
# ----
export PATH=$(echo $PATH | tr ':' '\n' | grep -v '/mnt/c' | tr '\n' ':')

. "$HOME/.local/bin/env"
# opencode
export PATH=/home/ejodry/.opencode/bin:$PATH

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# auto-activate .venv when entering a project tree
_auto_venv() {
  local dir="$PWD" found=""
  while :; do
    if [ -f "$dir/.venv/bin/activate" ]; then found="$dir/.venv"; break; fi
    [ "$dir" = "/" ] && break
    dir="${dir%/*}"; [ -z "$dir" ] && dir="/"
  done

  if [ -n "$found" ]; then
    if [ "$VIRTUAL_ENV" != "$found" ]; then
      [ -n "$_AUTO_VENV" ] && deactivate 2>/dev/null
      . "$found/bin/activate"
      _AUTO_VENV="$found"
    fi
  elif [ -n "$_AUTO_VENV" ]; then
    deactivate 2>/dev/null
    unset _AUTO_VENV
  fi
}
case "$PROMPT_COMMAND" in
  *_auto_venv*) ;;
  *) PROMPT_COMMAND="_auto_venv${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
esac

# emit cwd+branch to urxvt tabbed ext on each prompt (event-driven PR label)
_tab_pr_signal() {
  local br
  br=$(git symbolic-ref --short HEAD 2>/dev/null)
  printf '\033]777;tabpr;%s;%s\007' "$PWD" "$br"
  printf '\033]777;taboc;0\007'   # back at prompt: opencode not running
}
# flag opencode as running when launched (updates label live)
_tab_oc_preexec() {
  case "$BASH_COMMAND" in
    _tab_pr_signal*|_auto_venv*|_tab_oc_preexec*) return ;;
    opencode|opencode\ *|*/opencode|*/opencode\ *)
      printf '\033]777;taboc;1\007' ;;
  esac
}
trap '_tab_oc_preexec' DEBUG
case "$PROMPT_COMMAND" in
  *_tab_pr_signal*) ;;
  *) PROMPT_COMMAND="_tab_pr_signal${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
esac

opencode() {
  local state_file="$HOME/.config/opencode/current_provider"
  local provider
  provider="$(cat "$state_file" 2>/dev/null || echo anthropic)"
  local env_file="$HOME/.config/opencode/.env.$provider"
  [ -f "$env_file" ] && source "$env_file"
  command opencode "$@"
}

oc-provider() {
  if [ -z "${1:-}" ]; then
    cat "$HOME/.config/opencode/current_provider" 2>/dev/null || echo "anthropic (default)"
    return
  fi
  echo "$1" > "$HOME/.config/opencode/current_provider"
  echo "OpenCode provider set to: $1"
}

