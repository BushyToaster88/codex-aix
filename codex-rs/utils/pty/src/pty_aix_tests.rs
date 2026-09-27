use std::collections::HashMap;
use std::fs::File;
use std::os::fd::AsRawFd;
use std::path::Path;

use super::ChildFds;
use super::TerminalSize;
use super::open_unix_pty;
use super::spawn_process;

#[test]
fn native_pty_has_requested_size() -> anyhow::Result<()> {
    let (master, _) = open_unix_pty(TerminalSize { rows: 37, cols: 91 })?;
    let mut size = libc::winsize {
        ws_row: 0,
        ws_col: 0,
        ws_xpixel: 0,
        ws_ypixel: 0,
    };
    let result = unsafe {
        libc::ioctl(
            master.as_raw_fd(),
            libc::TIOCGWINSZ as _,
            &mut size as *mut _,
        )
    };
    assert_eq!(result, 0);
    assert_eq!((size.ws_row, size.ws_col), (37, 91));
    Ok(())
}

#[tokio::test]
async fn portable_and_preserving_fds_children_get_controlling_tty() -> anyhow::Result<()> {
    let fd = File::open("/dev/null")?;
    let attached = [fd.as_raw_fd()];
    for descriptors in [ChildFds::Inherited(&[]), ChildFds::Attached(&attached)] {
        let child = spawn_process(
            "/bin/sh",
            &["-c".to_owned(), ": </dev/tty".to_owned()],
            Path::new("/"),
            &HashMap::from([("SHELL".to_owned(), "/bin/sh".to_owned())]),
            &None,
            TerminalSize::default(),
            descriptors,
        )
        .await?;
        assert_eq!(child.exit_rx.await?, 0);
    }
    Ok(())
}
