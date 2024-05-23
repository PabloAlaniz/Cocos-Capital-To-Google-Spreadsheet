from trading import Trading

cocos = Trading()
cocos.insert_total_daily()
cocos.get_and_save_range_movements('2022-09-01')