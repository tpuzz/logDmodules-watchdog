"""Semantic event filter; public pull requests are only wake-up signals."""
REPOSITORY = 'tpuzz/logDmodules-watchdog'
PREFIXES = {
    'LOGDMODULES_RECOVERY_TEST': 'test',
    'LOGDMODULES_RECOVERY_TERMINAL': 'delivery',
    'LOGDMODULES_RECOVERY_INFRA_FAILURE': 'diagnostic',
    'LOGDMODULES_RECOVERY': 'recovery',
}


def classify_event(event):
    if not isinstance(event, dict) or event.get('action') != 'opened':
        return 'ignore'
    repository, pr = event.get('repository', {}), event.get('pull_request', {})
    if not isinstance(repository, dict) or not isinstance(pr, dict):
        return 'ignore'
    if repository.get('full_name') != REPOSITORY:
        return 'ignore'
    base = pr.get('base', {})
    if not isinstance(base, dict) or not isinstance(base.get('repo'), dict):
        return 'ignore'
    if base['repo'].get('full_name') != REPOSITORY:
        return 'ignore'
    title = pr.get('title')
    if not isinstance(title, str):
        return 'ignore'
    return next((kind for prefix, kind in PREFIXES.items()
                 if title == prefix or title.startswith(prefix + ' ')), 'ignore')
