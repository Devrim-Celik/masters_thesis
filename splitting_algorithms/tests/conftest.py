

def pytest_addoption(parser):
	parser.addoption("--mode", action = "store", default = "central_controller_complete")

def pytest_generate_tests(metafunc):
	# assign option_value to the (through command line) supplied mode
	option_value = metafunc.config.option.mode

	# if the function requires mode, supply it
	if "mode" in metafunc.fixturenames:
		metafunc.parametrize("mode", [option_value])