# Seven-State Classifier Report

Sample interval: 1.0 seconds
Labels: `['calibration_normal', 'computer_normal', 'computer_abnormal', 'reading_normal', 'reading_abnormal', 'ignore', 'absent']`

Samples: 4473
Label counts: `{'computer_normal': 2334, 'computer_abnormal': 429, 'reading_normal': 1405, 'ignore': 116, 'reading_abnormal': 188, 'calibration_normal': 1}`

| k | accuracy | train | test |
|---:|---:|---:|---:|
| 3 | 0.936 | 3578 | 895 |
| 5 | 0.932 | 3578 | 895 |
| 7 | 0.924 | 3578 | 895 |
| 9 | 0.918 | 3578 | 895 |
| 15 | 0.908 | 3578 | 895 |

Best k: `3`, accuracy: `0.936`

Best confusion:
- `computer_normal`: {'computer_normal': 438, 'reading_normal': 3, 'ignore': 3, 'computer_abnormal': 13}
- `reading_abnormal`: {'reading_abnormal': 23, 'reading_normal': 4}
- `ignore`: {'ignore': 17, 'reading_normal': 4, 'computer_normal': 4}
- `reading_normal`: {'reading_abnormal': 4, 'reading_normal': 284, 'computer_normal': 5, 'ignore': 1}
- `computer_abnormal`: {'computer_abnormal': 76, 'computer_normal': 16}
