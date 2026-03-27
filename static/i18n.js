window.LOCALES = {

  'zh-CN': {
    title: '简体中文',

    ERR: {
      wrong_password:             '密码错误',
      phone_and_content_required: '请填写号码和内容',
      send_failed:                '发送失败',
      no_fields_to_update:        '无更新字段',
    },

    NET_STAT: {
      not_registered:     '未注册',
      registered_home:    '已注册（本地）',
      searching:          '搜索中',
      rejected:           '被拒绝',
      registered_roaming: '已注册（漫游）',
      unknown:            '未知',
    },

    UI: {
      // Page
      pageTitle:   'SMS Gateway · 控制台',

      // Topbar
      detecting:   '检测中...',
      online:      '设备在线',
      offline:     '设备离线',
      btnRefresh:  '刷新',
      btnLogout:   '退出',

      // Tabs
      tabSend:     '📤 发送短信',
      tabInbox:    '📥 收件箱',
      tabOutbox:   '📤 发件箱',
      tabWebhooks: '🔗 Webhooks',
      tabLogs:     '📋 执行日志',
      tabModem:    '📶 Modem 状态',

      // Send SMS panel
      sendTitle:              '发送新短信',
      sendPhoneLabel:         '接收号码',
      sendContentLabel:       '短信内容',
      sendContentPlaceholder: '输入短信内容...',
      sendBtn:                '发送短信',
      sendBtnLoading:         '发送中...',
      sendOk:                 '短信发送成功',

      // Inbox / Outbox
      inboxTitle:  '收到的短信',
      outboxTitle: '已发送的短信',
      noMessages:  '暂无短信记录',
      prevPage:    '上一页',
      nextPage:    '下一页',
      pageInfo:    (page, pages, total) => `${page}/${pages}（共 ${total} 条）`,
      msgCount:    (n) => n + ' 条',

      // Device status
      deviceOnline:  '在线 ✓',
      deviceOffline: '离线 ✗',

      // Webhooks panel
      webhookTitle:          'Webhook 转发配置',
      addWebhook:            '+ 添加',
      noWebhooks:            '暂未配置 Webhook<br>点击上方按钮创建',
      addWebhookModalTitle:  '添加 Webhook',
      editWebhookModalTitle: '编辑 Webhook',
      webhookNameLabel:      '名称',
      webhookNamePlaceholder:'例如：Bark 通知',
      webhookTemplateLabel:  'Curl 模板 <span style="color:var(--text-faint);font-weight:400;">（占位符：##FROM## ##TO## ##CONTENT##）</span>',
      webhookPresetsLabel:   '快捷模板',
      presetWecom:           '企业微信机器人',
      presetDingtalk:        '钉钉机器人',
      presetGeneric:         '通用 JSON POST',
      webhookBtnTest:        '测试',
      webhookBtnEdit:        '编辑',
      webhookBtnDelete:      '删除',
      webhookSaved:          '已保存',
      webhookDeleted:        '已删除',
      webhookRequired:       '名称和模板必填',
      webhookTesting:        '正在测试...',
      webhookTestOk:         (code) => `测试成功 (HTTP ${code})`,
      webhookTestFail:       '测试失败: ',
      confirmDelete:         (name) => `确定删除「${name}」？`,
      btnSave:               '保存',
      btnCancel:             '取消',

      // Webhook logs panel
      logsTitle:       'Webhook 执行日志',
      allWebhooks:     '全部 Webhooks',
      clearLogs:       '清空日志',
      confirmClearOne: '确定清空当前 Webhook 的日志？',
      confirmClearAll: '确定清空所有 Webhook 日志？',
      logsCleared:     '日志已清空',
      noLogs:          '暂无执行日志',
      logTrigger:      '触发',
      logRequest:      '请求',
      logStatus:       '状态',
      logExpand:       '展开详情 ▾',
      logCollapse:     '收起详情 ▴',
      logSmsContent:   'SMS 内容:',
      logReqHeaders:   '请求 Headers:',
      logReqBody:      '请求 Body:',
      logRespBody:     '响应 Body:',
      logError:        '错误信息:',

      // Modem status panel
      modemInfoTitle:     'Modem 信息',
      modemRefresh:       '刷新',
      modemLoading:       '加载中...',
      modemDeviceTitle:   '设备状态',
      modemTtySmsLabel:   '短信串口 (TTY_SMS)',
      modemDeviceLabel:   '设备状态',
      modemPollLabel:     '轮询间隔',
      modemSmsCountLabel: 'Modem 存储短信数',
      modemSignal:        '信号强度',
      modemNetwork:       '网络注册',
      modemOperator:      '运营商',
      modemSim:           'SIM 状态',
      modemImei:          'IMEI',
      modemTtyAtWarning:  '⚠️ TTY_AT 未配置或设备不可用。请在容器环境变量中设置 <code style="font-family:var(--mono);">TTY_AT</code>（E3372 通常为 <code style="font-family:var(--mono);">/dev/ttyUSB0</code>）并重启容器。',

      // Misc
      refreshed: '已刷新',
      pollUnit:  's',
    },

    LOGIN: {
      pageTitle:           'SMS Gateway · 登录',
      subtitle:            'GSM Modem 短信管理平台',
      passwordLabel:       '访问密码',
      passwordPlaceholder: '请输入密码',
      loginBtn:            '登 录',
      loginBtnLoading:     '验证中...',
      errEmpty:            '请输入密码',
      errNetwork:          '网络错误',
    },

  },


  'zh-TW': {
    title: '繁體中文',

    ERR: {
      wrong_password:             '密碼錯誤',
      phone_and_content_required: '請填寫號碼和內容',
      send_failed:                '傳送失敗',
      no_fields_to_update:        '無更新欄位',
    },

    NET_STAT: {
      not_registered:     '未註冊',
      registered_home:    '已註冊（本地）',
      searching:          '搜尋中',
      rejected:           '已拒絕',
      registered_roaming: '已註冊（漫遊）',
      unknown:            '未知',
    },

    UI: {
      // Page
      pageTitle:   'SMS Gateway · 主控台',

      // Topbar
      detecting:   '偵測中...',
      online:      '裝置上線',
      offline:     '裝置離線',
      btnRefresh:  '重新整理',
      btnLogout:   '登出',

      // Tabs
      tabSend:     '📤 傳送簡訊',
      tabInbox:    '📥 收件匣',
      tabOutbox:   '📤 寄件匣',
      tabWebhooks: '🔗 Webhooks',
      tabLogs:     '📋 執行記錄',
      tabModem:    '📶 Modem 狀態',

      // Send SMS panel
      sendTitle:              '傳送新簡訊',
      sendPhoneLabel:         '接收號碼',
      sendContentLabel:       '簡訊內容',
      sendContentPlaceholder: '輸入簡訊內容...',
      sendBtn:                '傳送簡訊',
      sendBtnLoading:         '傳送中...',
      sendOk:                 '簡訊傳送成功',

      // Inbox / Outbox
      inboxTitle:  '收到的簡訊',
      outboxTitle: '已傳送的簡訊',
      noMessages:  '暫無簡訊記錄',
      prevPage:    '上一頁',
      nextPage:    '下一頁',
      pageInfo:    (page, pages, total) => `${page}/${pages}（共 ${total} 則）`,
      msgCount:    (n) => n + ' 則',

      // Device status
      deviceOnline:  '上線 ✓',
      deviceOffline: '離線 ✗',

      // Webhooks panel
      webhookTitle:          'Webhook 轉發設定',
      addWebhook:            '+ 新增',
      noWebhooks:            '尚未設定 Webhook<br>點擊上方按鈕建立',
      addWebhookModalTitle:  '新增 Webhook',
      editWebhookModalTitle: '編輯 Webhook',
      webhookNameLabel:      '名稱',
      webhookNamePlaceholder:'例如：Bark 通知',
      webhookTemplateLabel:  'Curl 範本 <span style="color:var(--text-faint);font-weight:400;">（占位符：##FROM## ##TO## ##CONTENT##）</span>',
      webhookPresetsLabel:   '快速範本',
      presetWecom:           '企業微信機器人',
      presetDingtalk:        '釘釘機器人',
      presetGeneric:         '通用 JSON POST',
      webhookBtnTest:        '測試',
      webhookBtnEdit:        '編輯',
      webhookBtnDelete:      '刪除',
      webhookSaved:          '已儲存',
      webhookDeleted:        '已刪除',
      webhookRequired:       '名稱和範本為必填',
      webhookTesting:        '測試中...',
      webhookTestOk:         (code) => `測試成功 (HTTP ${code})`,
      webhookTestFail:       '測試失敗: ',
      confirmDelete:         (name) => `確定刪除「${name}」？`,
      btnSave:               '儲存',
      btnCancel:             '取消',

      // Webhook logs panel
      logsTitle:       'Webhook 執行記錄',
      allWebhooks:     '全部 Webhooks',
      clearLogs:       '清除記錄',
      confirmClearOne: '確定清除此 Webhook 的記錄？',
      confirmClearAll: '確定清除所有 Webhook 記錄？',
      logsCleared:     '記錄已清除',
      noLogs:          '暫無執行記錄',
      logTrigger:      '觸發',
      logRequest:      '請求',
      logStatus:       '狀態',
      logExpand:       '展開詳情 ▾',
      logCollapse:     '收起詳情 ▴',
      logSmsContent:   'SMS 內容:',
      logReqHeaders:   '請求 Headers:',
      logReqBody:      '請求 Body:',
      logRespBody:     '回應 Body:',
      logError:        '錯誤訊息:',

      // Modem status panel
      modemInfoTitle:     'Modem 資訊',
      modemRefresh:       '重新整理',
      modemLoading:       '載入中...',
      modemDeviceTitle:   '裝置狀態',
      modemTtySmsLabel:   '簡訊串口 (TTY_SMS)',
      modemDeviceLabel:   '裝置',
      modemPollLabel:     '輪詢間隔',
      modemSmsCountLabel: 'Modem 儲存簡訊數',
      modemSignal:        '訊號強度',
      modemNetwork:       '網路註冊',
      modemOperator:      '電信業者',
      modemSim:           'SIM 狀態',
      modemImei:          'IMEI',
      modemTtyAtWarning:  '⚠️ TTY_AT 未設定或裝置不可用。請在容器環境變數中設定 <code style="font-family:var(--mono);">TTY_AT</code>（E3372 通常為 <code style="font-family:var(--mono);">/dev/ttyUSB0</code>）並重新啟動容器。',

      // Misc
      refreshed: '已重新整理',
      pollUnit:  's',
    },

    LOGIN: {
      pageTitle:           'SMS Gateway · 登入',
      subtitle:            'GSM Modem 簡訊管理平台',
      passwordLabel:       '存取密碼',
      passwordPlaceholder: '請輸入密碼',
      loginBtn:            '登 入',
      loginBtnLoading:     '驗證中...',
      errEmpty:            '請輸入密碼',
      errNetwork:          '網路錯誤',
    },

  },

  'en': {
    title: 'English',

    ERR: {
      wrong_password:             'Wrong password',
      phone_and_content_required: 'Phone number and message are required',
      send_failed:                'Send failed',
      no_fields_to_update:        'No fields to update',
    },

    NET_STAT: {
      not_registered:     'Not registered',
      registered_home:    'Registered (home)',
      searching:          'Searching',
      rejected:           'Rejected',
      registered_roaming: 'Registered (roaming)',
      unknown:            'Unknown',
    },

    UI: {
      // Page
      pageTitle:   'SMS Gateway · Console',

      // Topbar
      detecting:   'Detecting...',
      online:      'Online',
      offline:     'Offline',
      btnRefresh:  'Refresh',
      btnLogout:   'Logout',

      // Tabs
      tabSend:     '📤 Send SMS',
      tabInbox:    '📥 Inbox',
      tabOutbox:   '📤 Outbox',
      tabWebhooks: '🔗 Webhooks',
      tabLogs:     '📋 Logs',
      tabModem:    '📶 Modem',

      // Send SMS panel
      sendTitle:              'Send New SMS',
      sendPhoneLabel:         'Recipient',
      sendContentLabel:       'Message',
      sendContentPlaceholder: 'Type your message...',
      sendBtn:                'Send SMS',
      sendBtnLoading:         'Sending...',
      sendOk:                 'SMS sent successfully',

      // Inbox / Outbox
      inboxTitle:  'Received SMS',
      outboxTitle: 'Sent SMS',
      noMessages:  'No messages',
      prevPage:    'Previous',
      nextPage:    'Next',
      pageInfo:    (page, pages, total) => `${page}/${pages} (${total} total)`,
      msgCount:    (n) => `${n} msg${n === 1 ? '' : 's'}`,

      // Device status
      deviceOnline:  'Online ✓',
      deviceOffline: 'Offline ✗',

      // Webhooks panel
      webhookTitle:          'Webhook Forwarding',
      addWebhook:            '+ Add',
      noWebhooks:            'No webhooks configured<br>Click the button above to create one',
      addWebhookModalTitle:  'Add Webhook',
      editWebhookModalTitle: 'Edit Webhook',
      webhookNameLabel:      'Name',
      webhookNamePlaceholder:'e.g. Bark notification',
      webhookTemplateLabel:  'Curl Template <span style="color:var(--text-faint);font-weight:400;">(placeholders: ##FROM## ##TO## ##CONTENT##)</span>',
      webhookPresetsLabel:   'Quick Templates',
      presetWecom:           'WeCom Bot',
      presetDingtalk:        'DingTalk Bot',
      presetGeneric:         'Generic JSON POST',
      webhookBtnTest:        'Test',
      webhookBtnEdit:        'Edit',
      webhookBtnDelete:      'Delete',
      webhookSaved:          'Saved',
      webhookDeleted:        'Deleted',
      webhookRequired:       'Name and template are required',
      webhookTesting:        'Testing...',
      webhookTestOk:         (code) => `Test succeeded (HTTP ${code})`,
      webhookTestFail:       'Test failed: ',
      confirmDelete:         (name) => `Delete "${name}"?`,
      btnSave:               'Save',
      btnCancel:             'Cancel',

      // Webhook logs panel
      logsTitle:       'Webhook Logs',
      allWebhooks:     'All Webhooks',
      clearLogs:       'Clear Logs',
      confirmClearOne: 'Clear logs for this webhook?',
      confirmClearAll: 'Clear all webhook logs?',
      logsCleared:     'Logs cleared',
      noLogs:          'No execution logs',
      logTrigger:      'Trigger',
      logRequest:      'Request',
      logStatus:       'Status',
      logExpand:       'Show details ▾',
      logCollapse:     'Hide details ▴',
      logSmsContent:   'SMS Content:',
      logReqHeaders:   'Request Headers:',
      logReqBody:      'Request Body:',
      logRespBody:     'Response Body:',
      logError:        'Error:',

      // Modem status panel
      modemInfoTitle:     'Modem Info',
      modemRefresh:       'Refresh',
      modemLoading:       'Loading...',
      modemDeviceTitle:   'Device Status',
      modemTtySmsLabel:   'SMS Port (TTY_SMS)',
      modemDeviceLabel:   'Device',
      modemPollLabel:     'Poll Interval',
      modemSmsCountLabel: 'Messages in Modem',
      modemSignal:        'Signal',
      modemNetwork:       'Network',
      modemOperator:      'Operator',
      modemSim:           'SIM Status',
      modemImei:          'IMEI',
      modemTtyAtWarning:  '⚠️ TTY_AT is not configured or the device is unavailable. Set the <code style="font-family:var(--mono);">TTY_AT</code> environment variable (E3372 is typically <code style="font-family:var(--mono);">/dev/ttyUSB0</code>) and restart the container.',

      // Misc
      refreshed: 'Refreshed',
      pollUnit:  's',
    },

    LOGIN: {
      pageTitle:           'SMS Gateway · Login',
      subtitle:            'GSM Modem SMS Management',
      passwordLabel:       'Password',
      passwordPlaceholder: 'Enter password',
      loginBtn:            'Log In',
      loginBtnLoading:     'Verifying...',
      errEmpty:            'Please enter your password',
      errNetwork:          'Network error',
    },

  },

  'ja': {
    title: '日本語',

    ERR: {
      wrong_password:             'パスワードが違います',
      phone_and_content_required: '電話番号とメッセージを入力してください',
      send_failed:                '送信失敗',
      no_fields_to_update:        '更新するフィールドがありません',
    },

    NET_STAT: {
      not_registered:     '未登録',
      registered_home:    '登録済み（ホーム）',
      searching:          '検索中',
      rejected:           '拒否',
      registered_roaming: '登録済み（ローミング）',
      unknown:            '不明',
    },

    UI: {
      // Page
      pageTitle:   'SMS Gateway · コンソール',

      // Topbar
      detecting:   '検出中...',
      online:      'オンライン',
      offline:     'オフライン',
      btnRefresh:  '更新',
      btnLogout:   'ログアウト',

      // Tabs
      tabSend:     '📤 SMS送信',
      tabInbox:    '📥 受信トレイ',
      tabOutbox:   '📤 送信済み',
      tabWebhooks: '🔗 Webhooks',
      tabLogs:     '📋 実行ログ',
      tabModem:    '📶 モデム状態',

      // Send SMS panel
      sendTitle:              '新規SMS送信',
      sendPhoneLabel:         '宛先番号',
      sendContentLabel:       'メッセージ',
      sendContentPlaceholder: 'メッセージを入力...',
      sendBtn:                'SMS送信',
      sendBtnLoading:         '送信中...',
      sendOk:                 'SMS送信完了',

      // Inbox / Outbox
      inboxTitle:  '受信したSMS',
      outboxTitle: '送信したSMS',
      noMessages:  'メッセージなし',
      prevPage:    '前へ',
      nextPage:    '次へ',
      pageInfo:    (page, pages, total) => `${page}/${pages}（全${total}件）`,
      msgCount:    (n) => `${n}件`,

      // Device status
      deviceOnline:  'オンライン ✓',
      deviceOffline: 'オフライン ✗',

      // Webhooks panel
      webhookTitle:          'Webhook転送設定',
      addWebhook:            '+ 追加',
      noWebhooks:            'Webhookが設定されていません<br>上のボタンから作成してください',
      addWebhookModalTitle:  'Webhookを追加',
      editWebhookModalTitle: 'Webhookを編集',
      webhookNameLabel:      '名前',
      webhookNamePlaceholder:'例：Bark通知',
      webhookTemplateLabel:  'Curlテンプレート <span style="color:var(--text-faint);font-weight:400;">（プレースホルダー：##FROM## ##TO## ##CONTENT##）</span>',
      webhookPresetsLabel:   'クイックテンプレート',
      presetWecom:           'WeCom Bot',
      presetDingtalk:        'DingTalk Bot',
      presetGeneric:         '汎用 JSON POST',
      webhookBtnTest:        'テスト',
      webhookBtnEdit:        '編集',
      webhookBtnDelete:      '削除',
      webhookSaved:          '保存しました',
      webhookDeleted:        '削除しました',
      webhookRequired:       '名前とテンプレートは必須です',
      webhookTesting:        'テスト中...',
      webhookTestOk:         (code) => `テスト成功 (HTTP ${code})`,
      webhookTestFail:       'テスト失敗: ',
      confirmDelete:         (name) => `「${name}」を削除しますか？`,
      btnSave:               '保存',
      btnCancel:             'キャンセル',

      // Webhook logs panel
      logsTitle:       'Webhook実行ログ',
      allWebhooks:     '全てのWebhook',
      clearLogs:       'ログを削除',
      confirmClearOne: 'このWebhookのログを削除しますか？',
      confirmClearAll: '全Webhookのログを削除しますか？',
      logsCleared:     'ログを削除しました',
      noLogs:          '実行ログなし',
      logTrigger:      'トリガー',
      logRequest:      'リクエスト',
      logStatus:       'ステータス',
      logExpand:       '詳細を表示 ▾',
      logCollapse:     '詳細を閉じる ▴',
      logSmsContent:   'SMS内容:',
      logReqHeaders:   'リクエストHeaders:',
      logReqBody:      'リクエストBody:',
      logRespBody:     'レスポンスBody:',
      logError:        'エラー:',

      // Modem status panel
      modemInfoTitle:     'モデム情報',
      modemRefresh:       '更新',
      modemLoading:       '読み込み中...',
      modemDeviceTitle:   'デバイス状態',
      modemTtySmsLabel:   'SMSポート (TTY_SMS)',
      modemDeviceLabel:   'デバイス',
      modemPollLabel:     'ポーリング間隔',
      modemSmsCountLabel: 'モデム保存メッセージ数',
      modemSignal:        '信号強度',
      modemNetwork:       'ネットワーク登録',
      modemOperator:      'オペレーター',
      modemSim:           'SIM状態',
      modemImei:          'IMEI',
      modemTtyAtWarning:  '⚠️ TTY_ATが未設定またはデバイスが利用できません。コンテナの環境変数に <code style="font-family:var(--mono);">TTY_AT</code> を設定し（E3372は通常 <code style="font-family:var(--mono);">/dev/ttyUSB0</code>）、コンテナを再起動してください。',

      // Misc
      refreshed: '更新しました',
      pollUnit:  's',
    },

    LOGIN: {
      pageTitle:           'SMS Gateway · ログイン',
      subtitle:            'GSM Modem SMS管理',
      passwordLabel:       'パスワード',
      passwordPlaceholder: 'パスワードを入力',
      loginBtn:            'ログイン',
      loginBtnLoading:     '確認中...',
      errEmpty:            'パスワードを入力してください',
      errNetwork:          'ネットワークエラー',
    },

  },

};
